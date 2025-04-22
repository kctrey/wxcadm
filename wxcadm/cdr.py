from __future__ import annotations

from typing import Optional
from datetime import datetime, timedelta

import wxcadm.exceptions
from .common import *
from wxcadm import log


class LegPart:
    """ A Call Leg is made up of one or two Leg Parts """
    def __init__(self, record: dict):
        log.debug(f"Adding LegPart {record['Local call ID']}")
        self.record = record
        self.start_time = datetime.strptime(record['Start time'], "%Y-%m-%dT%H:%M:%S.%fZ")
        self.end_time = datetime.strptime(record['Release time'], "%Y-%m-%dT%H:%M:%S.%fZ")
        self.answer_time = None
        self.answered = True if record['Answered'] == 'true' else False
        self.local_id = record['Local call ID'] if record['Local call ID'] else None
        self.remote_id = record['Remote call ID'] if record['Remote call ID'] else None
        self.direction: str = record['Direction']
        self.calling_line_id: str = record['Calling line ID']
        self.called_line_id: str = record['Called line ID']
        self.dialed_digits: str = record['Dialed digits']
        self.user_number: str = record['User number']
        self.called_number: str = record['Called number']
        self.calling_number: str = record['Calling number']
        self.redirecting_number: str = record['Redirecting number']
        self.location_name: str = record['Location']
        self.user_type: str = record['User type']
        self.user: str = record['User']
        self.call_type = record['Call type']
        self.duration = record['Duration']
        self.time_offset = record['Site timezone']
        self.releasing_party: str = record['Releasing party']
        self.original_reason: str = record['Original reason']
        self.redirect_reason: str = record['Redirect reason']
        self.related_reason: str = record['Related reason']
        self.outcome: str = record['Call outcome']
        self.outcome_reason: str = record['Call outcome reason']
        self.ring_duration: str = record['Ring duration']
        self.device_owner_uuid: str = record['Device owner UUID']
        self.recording_platform: str = record['Call Recording Platform Name']
        self.recording_result: str = record['Call Recording Result']
        self.recording_trigger: str = record['Call Recording Trigger']
        try:
            self.device_mac: str = record['Device MAC']
        except KeyError:
            self.device_mac: str = record['Device Mac']
        # Transfer Identifiers
        if record['Call transfer time'] and record['Call transfer time'] != 'NA':
            self.transfer_time = datetime.strptime(record['Call transfer time'], "%Y-%m-%dT%H:%M:%S.%fZ")
        else:
            self.transfer_time = None

        if record['Transfer related call ID'] and record['Transfer related call ID'] != 'NA':
            self.transfer_related_call_id: str = record['Transfer related call ID']
        else:
            self.transfer_related_call_id = ''

        if record['Answer time'] and record['Answer time'] != 'NA':
            self.answer_time = datetime.strptime(record['Answer time'], "%Y-%m-%dT%H:%M:%S.%fZ")

        self.pstn_inbound: bool = True if record['Call type'].upper() == 'SIP_INBOUND' else False
        self.internal_call: bool = True if record['Call type'].upper() == 'SIP_ENTERPRISE' else False
        self.pstn_outbound = False
        if record['Call type'].upper() in ['SIP NATIONAL', 'SIP_INTERNATIONAL']:
            self.pstn_outbound = True


class CallLeg:
    """ A Call is made up of one ore more Call Legs """
    def __init__(self):
        # app.logger.debug("Adding Call Leg to Call")
        self.parts: list[LegPart] = []

    @property
    def start_time(self) -> datetime:
        """ The Call Leg start date and time

        Returns:
            datetime

        """
        return self.parts[0].start_time

    @property
    def end_time(self) -> datetime:
        """ The Call Leg end date and time

        Returns:
            datetime

        """
        for part in self.parts:
            if part.transfer_time is not None and part.direction.upper() == 'TERMINATING':
                return part.transfer_time
        return self.parts[-1].end_time

    @property
    def pstn_leg(self) -> bool:
        """ Whether this Call Leg is to or from the PSTN (off-net) """
        for part in self.parts:
            if part.pstn_inbound is True or part.pstn_outbound is True:
                return True
        return False

    @property
    def duration(self) -> int:
        """ The number of seconds of duration for the Call Leg """
        return int(self.parts[0].duration)

    @property
    def ring_duration(self) -> int:
        """ The number of seconds that the call was in a ringing state """
        return int(self.parts[0].ring_duration)

    @property
    def transfer_ids(self) -> list:
        """ List of Transfer IDs associated with the Call Leg

        Returns:
            list[str]

        """
        ids = []
        for part in self.parts:
            if part.transfer_related_call_id != '':
                ids.append(part.transfer_related_call_id)
        return ids

    @property
    def orig_part(self) -> Optional[LegPart]:
        """ The :class:`LegPart` for the originating part of the Call Leg"""
        for part in self.parts:
            if part.direction.upper() == 'ORIGINATING':
                return part
        return None

    @property
    def term_part(self) -> Optional[LegPart]:
        """ The :class:`LegPart` for the terminating part of the Call Leg """
        for part in self.parts:
            if part.direction.upper() == 'TERMINATING':
                return part
        return None

    @property
    def is_queue_leg(self) -> bool:
        """ Whether the Call Leg is to a Call Queue """
        if self.term_part is not None:
            if self.term_part.user_type.upper() == 'CALLCENTERPREMIUM':
                return True
        return False

    @property
    def is_aa_leg(self) -> bool:
        """ Whether the Call Leg is to an Auto Attendant """
        if self.term_part is not None:
            if self.term_part.user_type.upper() == 'AUTOMATEDATTENDANTVIDEO':
                return True
        return False

    @property
    def is_agent_leg(self) -> bool:
        """ Whether the Call Leg is a Call Queue leg to an Agent """
        if self.term_part is not None:
            if self.term_part.user_type.upper() == 'USER' and self.term_part.redirect_reason.upper() == 'CALLQUEUE':
                return True
        return False

    @property
    def is_vm_deposit(self) -> bool:
        """ Whether the Call Leg is a Voicemail deposit"""
        if self.orig_part is not None:
            if self.orig_part.called_line_id == 'Voice Portal Voice Messaging Group':
                if self.orig_part.redirect_reason in ['UserBusy', 'NoAnswer', 'Unconditional']:
                    return True
        return False

    @property
    def label(self) -> str:
        orig_part = self.orig_part
        term_part = self.term_part

        if term_part is not None and orig_part is not None:
            if term_part.user == '':
                if orig_part.called_line_id == 'NA':
                    return term_part.user_number
                else:
                    return orig_part.called_line_id
            else:
                return term_part.user
        elif term_part is not None and orig_part is None:
            if term_part.user == '':
                return term_part.user_number
            else:
                return term_part.user

    @property
    def calling_number(self) -> str:
        """ The Calling Part Number for the Call Leg """
        if self.orig_part is None:
            return self.term_part.calling_number
        else:
            return self.orig_part.calling_number

    @property
    def leg_description(self):
        desc = ""
        for part in self.parts:
            if part.user == '':
                endpoint = part.user_type
            else:
                endpoint = part.user
            if part.direction == "ORIGINATING":
                desc = f"From {endpoint}" + desc
            elif part.direction == 'TERMINATING':
                if part.pstn_inbound:
                    desc = desc + "SIP Inbound"
                desc = desc + f" to {endpoint}"
        return desc

    @property
    def new_leg_description(self) -> str:
        leg_from = ''
        leg_to = ''
        to_lock = False
        from_lock = False

        # Orig leg logic
        if self.orig_part is None:
            if self.term_part.call_type == 'SIP_INBOUND':
                leg_from = f'{self.term_part.calling_number}'
                from_lock = True
        else:
            if self.orig_part.user == '':
                if from_lock is False:
                    leg_from = self.orig_part.calling_number
            else:
                if from_lock is False:
                    leg_from = self.orig_part.user
                    from_lock = True
            if self.orig_part.called_line_id == 'NA' or self.orig_part.called_line_id == '':
                if to_lock is False:
                    leg_to = self.orig_part.called_number
            else:
                if to_lock is False:
                    leg_to = self.orig_part.called_line_id
                    to_lock = True

        # Term Leg logic
        if self.term_part is None:
            if self.orig_part.user == '':
                if from_lock is False:
                    leg_from = self.orig_part.calling_number
            else:
                leg_from = self.orig_part.user
                from_lock = True
            if to_lock is False:
                leg_to = f"{self.orig_part.called_number}"
        else:
            if self.term_part.calling_line_id == 'NA' or self.term_part.calling_line_id == '':
                if from_lock is False:
                    leg_from = self.term_part.calling_number
            else:
                if from_lock is False:
                    leg_from = self.term_part.calling_line_id
                    from_lock = True
            if self.term_part.user == '':
                if to_lock is False:
                    leg_to = self.term_part.called_number
            else:
                if to_lock is False:
                    leg_to = self.term_part.user
                    to_lock = True

        description = f"From {leg_from}"
        if self.out_reason:
            description += f' ({self.out_reason})'
        description += f' to {leg_to}'
        if self.in_reason:
            description += f' ({self.in_reason})'
        return description

    @property
    def in_reason(self) -> Optional[str]:
        """ The Reason a Call Leg was received.

        Returns:
            str: A descriptive reason

        """
        if self.term_part is None:
            return None
        if self.term_part.call_type == 'SIP_INBOUND':
            return 'SIP Inbound'
        if self.term_part.redirect_reason == '':
            return None
            # More to do here when we figure out all the reasons a call will come in
        else:
            return self.term_part.redirect_reason

    @property
    def out_reason(self) -> Optional[str]:
        """ The Reason the Call Leg originated.

        This can be useful in finding Call Queue Call-Back legs

        Returns:
            str: A descriptive reason

        """
        if self.orig_part is None:
            return None
        if self.orig_part.related_reason == '':
            return None
        else:
            if self.orig_part.user_type == 'CallCenterPremium' and self.orig_part.related_reason == 'Unrecognised':
                return 'Queue Callback'
            else:
                return self.orig_part.related_reason

    @property
    def out_label(self):
        """ An experimental text description of the Call Leg """
        label = ''
        if self.orig_part is None:
            # Without an Orig Part, we have to get everything we need from the Term Part
            if self.term_part.call_type == 'SIP_INBOUND':
                label += 'SIP Inbound '
            if self.term_part.calling_line_id != '':
                label += f"from {self.term_part.calling_line_id} ({self.term_part.calling_number}) "
        if self.orig_part.call_type == 'SIP_ENTERPRISE':
            if self.orig_part.user == '':
                pass
            else:
                return self.orig_part.user
            return None

    @property
    def parts_id(self) -> list:
        parts_id = []
        for part in self.parts:
            if part.local_id is not None:
                parts_id.append(part.local_id)
            if part.remote_id is not None:
                parts_id.append(part.remote_id)
        return parts_id

    @property
    def answered(self) -> bool:
        """ Whether the Call Leg was answered

        Returns:
            bool

        """
        answered = False
        for part in self.parts:
            if part.answered is True:
                answered = True
        return answered

    @property
    def answered_label(self) -> str:
        """ The string 'Answered' or 'Unanswered'. Useful for labeling in a UI. """
        label = 'Answered' if self.answered is True else 'Unanswered'
        return label

    def add_part(self, record: dict) -> LegPart:
        part = LegPart(record)
        self.parts.append(part)
        return part

    @property
    def recorded(self) -> bool:
        """ Whether the Call Leg was recorded """
        recorded = False
        for part in self.parts:
            if part.recording_result.lower() == 'successful':
                recorded = True
        return recorded

class Call:
    def __init__(self, correlation_id: str):
        self.id: str = correlation_id
        self.legs = []
        self.correlation_ids = [correlation_id]
        log.debug("New Call instance created")

    def add_record(self, record: dict):
        log.debug(f"Adding Record to Call {self.id}")
        # Determine if the Local or Remote CallPart IDs have been seen already
        existing_leg = False
        for leg in self.legs:
            if record['Local call ID'] in leg.parts_id or record['Remote call ID'] in leg.parts_id:
                existing_leg = True
                leg.add_part(record)
        if existing_leg is False:
            new_leg = CallLeg()
            self.legs.append(new_leg)
            new_leg.add_part(record)

    @property
    def start_time(self) -> Optional[datetime]:
        """ The Call Start date and time

        Returns:
            datetime

        """
        earliest: Optional[datetime] = None
        for leg in self.legs:
            if earliest is None or leg.start_time < earliest:
                earliest = leg.start_time
        return earliest

    @property
    def end_time(self) -> Optional[datetime]:
        """ The Call End date and time

        Returns:
            datetime

        """
        latest: Optional[datetime] = None
        for leg in self.legs:
            if latest is None or leg.end_time > latest:
                latest = leg.end_time
        return latest

    @property
    def duration(self):
        """ The duration of the Call

        Returns:
            timedelta

        """
        difference: timedelta = self.end_time - self.start_time
        return str(difference).split('.')[0]

    @property
    def calling_number(self) -> str:
        """ The original Calling Number from the first Leg of the Call

        Returns:
            str: The Calling Number

        """
        return self.legs_sorted[0].calling_number

    @property
    def leg_count(self) -> int:
        """ The number of Legs that make up the call

        Returns:
            int: Number of Legs

        """
        return len(self.legs)

    @property
    def legs_sorted(self):
        """ List of Call Legs sorted by their Start DateTime

        Returns:
            list[CallLeg]: The list of CallLegs

        """
        return sorted(self.legs, key=lambda x: x.start_time, reverse=False)

    @property
    def part_ids(self):
        """ List of Part IDs used within the Call """
        parts = []
        for leg in self.legs:
            parts.extend(leg.parts_id)
        return set(parts)

    @property
    def transfer_ids(self) -> list:
        """ List of Transfer IDs used within the Call """
        ids = []
        for leg in self.legs:
            ids.extend(leg.transfer_ids)
        return ids

    @property
    def _missing_part_ids(self) -> list:
        missing = []
        for id in self.transfer_ids:
            if id not in self.part_ids:
                missing.append(id)
        return missing

    @property
    def answered_legs(self):
        """ The number of Call Legs where the Answer indicator is True

        Returns:
            int: The number of Answered legs

        """
        answered = 0
        for leg in self.legs:
            if leg.answered is True:
                answered += 1
        return answered

    @property
    def has_queue_leg(self) -> bool:
        """ Whether the Call has a Call Leg that involves a Call Queue

        Returns:
            bool

        """
        for leg in self.legs:
            if leg.is_queue_leg is True:
                return True
        return False

    @property
    def has_pstn_leg(self) -> bool:
        """ Whether the Call has a Call Leg that was to or from the PSTN (off-net)

        Returns:
            bool

        """
        for leg in self.legs:
            if leg.pstn_leg:
                return True
        return False

    @property
    def has_vm_deposit_leg(self) -> bool:
        """ Whether the Call contains a Voicemail deposit

        Returns:
            bool

        """
        for leg in self.legs:
            if leg.is_vm_deposit:
                return True
        return False

    @property
    def is_queue_abandon(self) -> bool:
        """ Whether the Call is one where the caller ended the call while waiting in a Call Queue

        Returns:
             bool

        """
        if self.has_queue_leg:
            for leg in self.legs:
                if leg.is_agent_leg and leg.answered:
                    return False
            return True
        else:
            return False


class CallDetailRecords:
    def __init__(self, records: list, webex: Optional[wxcadm.Webex] = None):
        """ The main class to process and work with Call Detail Records (CDRs). CDRs can be obtained in various ways.
        This calls takes the records that have been obtained via one of these methods and builds a more useful
        structure to describe the records. This structure makes it easier to find calls and analyze features that are
        used by the legs involved in a call.

        This class contains a list of :class:`Call`s. A :class:`Call` is made up of one or more :class:`CallLeg`s,
        which are a connection between two endpoints. A :class:`CallLeg` is made up of one or two :class:`CallParts`,
        which are the records for each endpoint. There may be an 'Orig Part', the record from the endpoint originating
        the call leg, a 'Term Part', the record for the endpoint receiving the call leg, or both. Only when an endpoint
        is a Webex Calling controlled endpoint will there be a :class:`LegPart`. For example, in a
        :class:`CallLeg` from the PSTN to a Webex Calling user, only the 'Term Part' will be present because Webex
        Calling does not control the PSTN endpoint.

        Examples:
            .. code-block:: python


        Args:
            records (list[dict]): A list of records where each record is a dict with the raw CDR field name
            webex (wxcadm.Webex): A :class:`.webex.Webex` instance to provide a data channel to use the Webex APIs

        """
        self.records: list = records
        """ The records that were sent to the CallDetailRecords instance """
        self.webex = webex
        """ The wxcadm.Webex connection to use to look up identifiers """
        self._retry_records = []
        self.calls: list[Call] = []
        """ The (unordered) list of Call instances after processing """
        self.__process_calls()
        # Retry any that didn't make it through the first time
        self._to_merge = []
        self.__merge_transfer_calls()

    def get_call_by_correlation_id(self, correlation_id: str) -> Optional[Call]:
        """ Find a Call by its Correlation ID

        Args:
            correlation_id (str): The Correlation ID to search for

        Returns:
            Call: The matching Call instance

        """
        log.debug(f"Getting Call by Correlation ID: {correlation_id}")
        for call in self.calls:
            if correlation_id == call.id:
                return call
        return None

    def get_call_by_part_call_id(self, part_call_id: str):
        """ Find a Call by the Part ID of one of the Call Parts

        Searching by Part iD is rare and normally only used for internal processing, but users who have an idea of
        what the Part ID is might have use for this method.

        Returns:
            Call: The matching Call instance

        """
        log.debug(f"Getting Call by Park Call ID: {part_call_id}")
        for call in self.calls:
            if part_call_id in call.part_ids:
                return call
        return None

    @property
    def calls_sorted(self):
        """ A list of Calls sorted by timestamp """
        return sorted(self.calls, key=lambda x: x.start_time, reverse=False)

    def __user_finder(self, type: str, location_id: str = None, user_id: str = None) -> str:
        log.info(f"Finding User with type '{type}' and ID {user_id}")
        if type.lower() == 'user':
            me = self.webex.org.people.get(uuid=user_id)
            if me is not None:
                log.debug(f"Found User with ID {user_id}")
                return f"{user_id} ({me.display_name})"
            else:
                log.warning(f"Could not find User with ID {user_id}")
                return user_id
        elif type.lower() == 'automatedattendantvideo':
            me = self.webex.org.auto_attendants.get(uuid=user_id)
            if me is not None:
                log.debug(f"Found match: {me.name}")
                return me.name
            else:
                log.warning("No User Match found")
                return 'Auto Attendant'
        elif type.lower() == 'callcenterpremium':
            me = self.webex.org.call_queues.get(uuid=user_id)
            if me is not None:
                log.debug(f"Found match: {me.name}")
                return me.name
            else:
                log.warning("No User Match found")
                return 'Call Queue'
        elif type.lower() == 'place':
            me = self.webex.org.workspaces.get(uuid=user_id)
            if me is not None:
                log.debug(f"Found match: {me.name}")
                return me.name
            else:
                log.warning("No User Match found")
                return 'Workspace'
        else:
            log.warning(f"No Method to find User for {type}")
        return f'{type} - {user_id}'

    def __process_calls(self, records: Optional[list] = None):
        log.debug("Processing calls for CallDetailRecords")
        if records is None:
            records = self.records

        for record in records:
            # app.logger.debug(f"Correlation ID: {record['Correlation ID']}")
            if record['User'] == '' or record['User'] == 'NA':
                record['User'] = self.__user_finder(
                    record['User type'],
                    record['Site UUID'],
                    record['User UUID']
                )
            call = self.get_call_by_correlation_id(record['Correlation ID'])
            # Create a new Call record if we haven't seen this Correlation ID yet
            if call is None:
                log.debug(f"New Correlation ID {record['Correlation ID']}. Creating Call")
                call = Call(record['Correlation ID'])
                self.calls.append(call)
            call.add_record(record)

    def __delete_call(self, id: str):
        new_calls = []
        for call in self.calls:
            if call.id != id:
                new_calls.append(call)
        self.calls = new_calls

    def __merge_transfer_calls(self):
        merge_done = False
        # This is done as a while loop that never ends without a break. Since matching calls will both have each others
        # part_id values, we have to take them one at a time without looking at the self.calls for the loop.
        while merge_done is False:
            to_process = []
            for call in self.calls:
                if len(call._missing_part_ids) > 0:
                    to_process.append(call)

            if len(to_process) == 0:
                break

            call = to_process[0]
            missing_id = call._missing_part_ids[0]

            id_to_find = missing_id
            for search_call in self.calls:
                if missing_id in search_call.part_ids and \
                        (search_call.start_time - timedelta(hours=24) <=
                         call.start_time <=
                         search_call.start_time + timedelta(hours=24)):
                    self.__merge_calls(call, search_call)
                    break

    def __merge_calls(self, call1: Call, call2: Call):
        new_calls_list = []
        for call in self.calls:
            if call == call1:
                call.legs.extend(call2.legs)
                call.correlation_ids.extend(call2.correlation_ids)
                new_calls_list.append(call)
            elif call == call2:
                continue
            else:
                new_calls_list.append(call)
        self.calls = new_calls_list
        return self.calls

    def get_abandoned_calls(self) -> list:
        """ Get a list of Calls where the caller hung up in a Call Queue prior to an Agent answering

        Returns:
            list[Call]: A list of Call instances

        """
        response = []
        for call in self.calls_sorted:
            if call.has_queue_leg and call.is_queue_abandon:
                response.append(call)
        return response

    def get_pstn_calls(self) -> list:
        """ Get a list of Calls where a PSTN leg is present

        Returns:
            list[Call]: A list of Call instances

        """
        response = []
        for call in self.calls_sorted:
            if call.has_pstn_leg:
                response.append(call)
        return response

    def get_voicemail_deposit_calls(self) -> list:
        """ Get a list of Calls where the call was sent to Voicemail for the caller to leave a message

        Returns:
            list[Call]: A list of Call instances

        """
        response = []
        for call in self.calls_sorted:
            if call.has_vm_deposit_leg:
                response.append(call)
        return response

from __future__ import annotations

from typing import Optional
from datetime import datetime, timedelta

import wxcadm.exceptions
from .common import *
from wxcadm import log


class LegPart:
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
    def __init__(self):
        # app.logger.debug("Adding Call Leg to Call")
        self.parts: list[LegPart] = []

    @property
    def start_time(self) -> datetime:
        return self.parts[0].start_time

    @property
    def end_time(self) -> datetime:
        for part in self.parts:
            if part.transfer_time is not None and part.direction.upper() == 'TERMINATING':
                return part.transfer_time
        return self.parts[-1].end_time

    @property
    def pstn_leg(self) -> bool:
        for part in self.parts:
            if part.pstn_inbound is True or part.pstn_outbound is True:
                return True
        return False

    @property
    def duration(self) -> int:
        return int(self.parts[0].duration)

    @property
    def ring_duration(self) -> int:
        return int(self.parts[0].ring_duration)

    @property
    def transfer_ids(self) -> list:
        ids = []
        for part in self.parts:
            if part.transfer_related_call_id != '':
                ids.append(part.transfer_related_call_id)
        return ids

    @property
    def orig_part(self) -> Optional[LegPart]:
        for part in self.parts:
            if part.direction.upper() == 'ORIGINATING':
                return part
        return None

    @property
    def term_part(self) -> Optional[LegPart]:
        for part in self.parts:
            if part.direction.upper() == 'TERMINATING':
                return part
        return None

    @property
    def is_queue_leg(self) -> bool:
        if self.term_part is not None:
            if self.term_part.user_type.upper() == 'CALLCENTERPREMIUM':
                return True
        return False

    @property
    def is_aa_leg(self) -> bool:
        if self.term_part is not None:
            if self.term_part.user_type.upper() == 'AUTOMATEDATTENDANTVIDEO':
                return True
        return False

    @property
    def is_agent_leg(self) -> bool:
        if self.term_part is not None:
            if self.term_part.user_type.upper() == 'USER' and self.term_part.redirect_reason.upper() == 'CALLQUEUE':
                return True
        return False

    @property
    def is_vm_deposit(self) -> bool:
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
        answered = False
        for part in self.parts:
            if part.answered is True:
                answered = True
        return answered

    @property
    def answered_label(self) -> str:
        label = 'Answered' if self.answered is True else 'Unanswered'
        return label

    def add_part(self, record: dict) -> LegPart:
        part = LegPart(record)
        self.parts.append(part)
        return part


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
        earliest: Optional[datetime] = None
        for leg in self.legs:
            if earliest is None or leg.start_time < earliest:
                earliest = leg.start_time
        return earliest

    @property
    def end_time(self) -> Optional[datetime]:
        latest: Optional[datetime] = None
        for leg in self.legs:
            if latest is None or leg.end_time > latest:
                latest = leg.end_time
        return latest

    @property
    def duration(self):
        difference: timedelta = self.end_time - self.start_time
        return str(difference).split('.')[0]

    @property
    def calling_number(self) -> str:
        return self.legs_sorted[0].calling_number

    @property
    def leg_count(self) -> int:
        return len(self.legs)

    @property
    def legs_sorted(self):
        return sorted(self.legs, key=lambda x: x.start_time, reverse=False)

    @property
    def part_ids(self):
        parts = []
        for leg in self.legs:
            parts.extend(leg.parts_id)
        return set(parts)

    @property
    def transfer_ids(self) -> list:
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
        answered = 0
        for leg in self.legs:
            if leg.answered is True:
                answered += 1
        return answered

    @property
    def has_queue_leg(self) -> bool:
        for leg in self.legs:
            if leg.is_queue_leg is True:
                return True
        return False

    @property
    def has_pstn_leg(self) -> bool:
        for leg in self.legs:
            if leg.pstn_leg:
                return True
        return False

    @property
    def has_vm_deposit_leg(self) -> bool:
        for leg in self.legs:
            if leg.is_vm_deposit:
                return True
        return False

    @property
    def is_queue_abandon(self) -> bool:
        if self.has_queue_leg:
            for leg in self.legs:
                if leg.is_agent_leg and leg.answered:
                    return False
            return True
        else:
            return False


class CallDetailRecords:
    def __init__(self, records: list, webex: Optional[wxcadm.Webex] = None):
        self.records: list = records
        self.webex = webex
        self.retry_records = []
        self.calls: list[Call] = []
        self.process_calls()
        # Retry any that didn't make it through the first time
        self.to_merge = []
        self.merge_transfer_calls()

    def get_call_by_correlation_id(self, correlation_id: str) -> Optional[Call]:
        log.debug(f"Getting Call by Correlation ID: {correlation_id}")
        for call in self.calls:
            if correlation_id == call.id:
                return call
        return None

    def get_call_by_part_call_id(self, part_call_id: str):
        log.debug(f"Getting Call by Park Call ID: {part_call_id}")
        for call in self.calls:
            if part_call_id in call.part_ids:
                return call
        return None

    @property
    def calls_sorted(self):
        return sorted(self.calls, key=lambda x: x.start_time, reverse=False)

    def user_finder(self, type: str, location_id: str, user_id: str) -> str:
        log.info(f"Finding User with type '{type}' and ID {user_id}")
        if type == 'AutomatedAttendantVideo':
            me = self.webex.org.auto_attendants.get(uuid=user_id)
            if me is not None:
                log.debug(f"Found match: {me.name}")
                return me.name
            else:
                log.warning("No User Match found")
                return 'Auto Attendant'
        elif type == 'CallCenterPremium':
            me = self.webex.org.call_queues.get(uuid=user_id)
            if me is not None:
                log.debug(f"Found match: {me.name}")
                return me.name
            else:
                log.warning("No User Match found")
                return 'Call Queue'
        elif type == 'Place':
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

    def process_calls(self, records: Optional[list] = None):
        log.debug("Processing calls for CallDetailRecords")
        if records is None:
            records = self.records

        for record in records:
            # app.logger.debug(f"Correlation ID: {record['Correlation ID']}")
            if record['User'] == '' or record['User'] == 'NA':
                record['User'] = self.user_finder(
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

    def delete_call(self, id: str):
        new_calls = []
        for call in self.calls:
            if call.id != id:
                new_calls.append(call)
        self.calls = new_calls

    def merge_transfer_calls(self):
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
                    self.merge_calls(call, search_call)
                    break

    def merge_calls(self, call1: Call, call2: Call):
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
        response = []
        for call in self.calls_sorted:
            if call.has_queue_leg and call.is_queue_abandon:
                response.append(call)
        return response

    def get_pstn_calls(self) -> list:
        response = []
        for call in self.calls_sorted:
            if call.has_pstn_leg:
                response.append(call)
        return response

    def get_voicemail_deposit_calls(self) -> list:
        response = []
        for call in self.calls_sorted:
            if call.has_vm_deposit_leg:
                response.append(call)
        return response

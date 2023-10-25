from __future__ import annotations

import os
from dataclasses import dataclass, field
from collections import UserList
from requests_toolbelt import MultipartEncoder

import wxcadm.org
from wxcadm import log
from .common import *

class AnnouncementList(UserList):
    def __init__(self, parent: wxcadm.Org):
        super().__init__()
        log.debug("Initializing AnnouncementList instance")
        self.parent: wxcadm.Org = parent
        self.data: list = self._get_announcements()

    def _get_announcements(self):
        annc_list = []
        announcements = webex_api_call("get", "v1/telephony/config/announcements", params={'locationId': 'all'})
        for annc in announcements['announcements']:
            this_annc = Announcement(parent=self.parent, **annc)
            annc_list.append(this_annc)
        return annc_list

    def _refresh_announcements(self):
        self.data = self._get_announcements()

    def get_by_location_id(self, location_id: str) -> list[Announcement]:
        """ Get the :py:class:`Announcement` instances for the given location_id

        This will only return :py:class:`Announcement` entries which are defined at the Location level. It will not
        include any :py:class:`Announcement` that is defined at the Organization level.

        Args:
            location_id (str): The Location ID to filer on

        Returns:
            list[Announcement]: A list of the :py:class:`Announcement` instances for the given location. If none
                are found, an empty list will be returned.

        """
        annc_list = []
        for annc in self.data:
            if annc.level == "LOCATION" and annc.location['id'] == location_id:
                annc_list.append(annc)

        return annc_list

    def get_by_id(self, id: str) -> Announcement | None:
        """ Ge the :py:class:`Announcement` instance with the given ID

        Args:
            id (str): The Announcement ID

        Returns:
            Announcement: The matching :py:class:`Announcement` instance. None is returned if no match can be found.

        """
        for annc in self.data:
            if annc.id == id:
                return annc
        return None

    @property
    def stats(self):
        """ The repository usage for announcements within the Org """
        response = webex_api_call("get", "v1/telephony/config/announcements/usage", params={"orgId": self.parent.id})
        return response

    def upload(self, name: str, filename: str, location = None):
        """ Upload a new announcement file

        Args:
            name (str): The unique name of the Announcement
            filename (str): The path to the WAV file to upload
            location (str | Location, optional): The Location ID or Location instance to associate the uploaded
                announcement to. If not present, the announcement will be uploaded at the Organization level.

        Returns:
            str: The ID of the created Announcement

        """
        log.info(f"Uploading Announcement {name} with file: {filename}")
        upload_as = os.path.basename(filename)
        content = open(filename, "rb")
        must_close = True
        encoder = MultipartEncoder(
            fields={"name": name,
                    "file": (upload_as, content, 'audio/wav')
                    }
        )
        log.debug(f"Location is: {type(location)}")

        if location is not None:
            # Upload at the Location level
            if isinstance(location, wxcadm.location.Location):
                log.info(f"Uploading to Location: {location.name}")
                location_id = location.id
            else:
                log.info(f"Uploading to Location ID: {location}")
                location_id = location
            url = f"v1/telephony/config/locations/{location_id}/announcements"
        else:
            # Upload at the Org level
            log.info("Uploading to Organization")
            url = "v1/telephony/config/announcements"

        response = webex_api_call("post_upload",
                                  url,
                                  payload=encoder)

        if must_close is True:
            content.close()

        log.debug("Response:")
        log.debug(f"\t{response}")
        self._refresh_announcements()
        return response['id']

@dataclass
class Announcement:
    parent: wxcadm.Org = field(repr=False)
    id: str
    name: str
    fileName: str
    fileSize: str = field(repr=False)
    mediaFileType: str = field(repr=False)
    lastUpdated: str = field(repr=False)
    level: str
    location: dict | None = field(default=None)

    @property
    def used_by(self):
        """ The list of call features this announcement is assigned to """
        used_by = []

        if self.level.lower() == "organization":
            url = f"v1/telephony/config/announcements/{self.id}"
        elif self.level.lower() == "location":
            url = f"v1/telephony/config/locations/{self.location['id']}/announcements/{self.id}"

        response = webex_api_call("get", url)
        if response.get('featureReferences', None) is not None:
            for usage in response.get('featureReferences'):
                item = {
                    "id": usage['id'],
                    "name": usage['name'],
                    "type": usage['type'],
                    "location": self.parent.get_location(id=usage['locationId']),
                }
                if usage['type'] == 'Call Queue':
                    cq = self.parent.get_call_queue_by_id(usage['id'])
                    item['instance'] = cq
                used_by.append(item)
        return used_by

    @property
    def in_use(self):
        """ Boolean whether the Announcement is being used by a calling feature """
        if len(self.used_by) > 0:
            return True
        else:
            return False

    def replace_file(self, filename: str):
        """ Replace the existing audio file with a new one

        Args:
            filename:

        Returns:

        """
        log.info(f"Replacing {self.name} file with file: {filename}")
        upload_as = os.path.basename(filename)
        content = open(filename, "rb")
        must_close = True
        encoder = MultipartEncoder(
            fields={"name": self.name,
                    "file": (upload_as, content, 'audio/wav')
                    }
        )

        if self.level.lower() == "organization":
            url = f"v1/telephony/config/announcements/{self.id}"
        elif self.level.lower() == "location":
            url = f"v1/telephony/config/locations/{self.location['id']}/announcements/{self.id}"

        response = webex_api_call("put_upload", url, payload=encoder)

        if must_close is True:
            content.close()

        log.debug("Response:")
        log.debug(f"\t{response}")
        return True

    def delete(self):
        """ Delete the Announcement

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f"Deleting Announcement {self.name} at the {self.level.title()} level")
        if self.in_use is True:     # No use even trying to delete one in use
            return False

        if self.level.lower() == "organization":
            url = f"v1/telephony/config/announcements/{self.id}"
        elif self.level.lower() == "location":
            url = f"v1/telephony/config/locations/{self.location['id']}/announcements/{self.id}"

        response = webex_api_call("delete", url)
        log.debug(f"Response: {response}")
        return True

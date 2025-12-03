from __future__ import annotations

import os
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, config
from collections import UserList
from requests_toolbelt import MultipartEncoder

import wxcadm.org
from wxcadm import log


class AnnouncementList(UserList):
    def __init__(self, org: wxcadm.Org):
        super().__init__()
        log.debug("Initializing AnnouncementList instance")
        self.org: wxcadm.Org = org
        self.data: list = self._get_announcements()

    def _get_announcements(self):
        log.debug("Getting announcements")
        annc_list = []
        response = self.org.api.get("v1/telephony/config/announcements",
                                       params={'locationId': 'all'}, items_key='announcements')
        for annc in response:
            this_annc = Announcement(org=self.org, **annc)
            annc_list.append(this_annc)
        return annc_list

    def _refresh_announcements(self):
        log.debug("Refreshing announcements")
        self.data = self._get_announcements()

    def get(self, id:str = None,
            name:str = None,
            file_name: str = None,
            level: str = None,
            location: wxcadm.Location = None) -> Announcement | list[Announcement] | None:
        """ Get the Announcements matching the given criteria.

        Args:
            id (str, optional): The ID of the Announcement
            name (str, optional): The name of the Announcement
            file_name (str, optional) : The name of the file associated with the Announcement
            level (str, optional) : The level of the Announcement (e.g. ORGANIZATION, LOCATION)
            location (Location, optional) : The Location instance to filter on

        Returns:
            Announcement | list[Announcement] | None: The matching Announcements. If more than one Announcement is found,
                a list of Announcements is returned. If no Announcements are found, None is returned.

        """
        filtered_announcements = []
        for annc in self.data:
            match = True
            if id is not None and annc.id != id:
                match = False
            if name is not None and name not in annc.name:
                match = False
            if file_name is not None and annc.fileName != file_name:
                match = False
            if level is not None and annc.level != level:
                match = False
            if location is not None:
                if annc.level == 'ORGANIZATION':
                    match = False
                else:
                    if annc.location is not None and annc.location['id'] != location.id:
                        match = False

            if match is True:
                filtered_announcements.append(annc)

        if len(filtered_announcements) == 1:
            return filtered_announcements[0]
        elif len(filtered_announcements) > 1:
            return filtered_announcements
        else:
            return None

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
        log.debug(f"Getting announcements by location id: {location_id}")
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
        log.debug(f"Getting announcements by id: {id}")
        for annc in self.data:
            if annc.id == id:
                return annc
        return None

    @property
    def stats(self):
        """ The repository usage for announcements within the Org """
        log.debug("Getting stats")
        response = self.org.api.get("v1/telephony/config/announcements/usage")
        return response

    def upload(self, name: str, filename: str, location: str | wxcadm.Location = None):
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

        response = self.org.api.post_upload(url, payload=encoder)

        if must_close is True:
            content.close()

        log.debug("Response:")
        log.debug(f"\t{response}")
        self._refresh_announcements()
        return response['id']


@dataclass
class Announcement:
    org: wxcadm.Org = field(repr=False)
    id: str
    """ The ID of the Announcement """
    name: str
    """ The name of the Announcement """
    fileName: str
    """ The name of the file associated with the Announcement """
    fileSize: str = field(repr=False)
    """ The size of the file associated with the Announcement in bytes """
    mediaFileType: str = field(repr=False)
    """ The type of the file associated with the Announcement """
    lastUpdated: str = field(repr=False)
    """ The timestamp the Announcement was last updated """
    level: str
    """ The level of the Announcement (e.g. ORGANIZATION, LOCATION) """
    location: dict | None = field(default=None)
    """ The Location instance associated with the Announcement """

    @property
    def used_by(self):
        """ The list of call features this announcement is assigned to """
        used_by = []

        if self.level.lower() == "organization":
            url = f"v1/telephony/config/announcements/{self.id}"
        elif self.level.lower() == "location":
            url = f"v1/telephony/config/locations/{self.location['id']}/announcements/{self.id}"
        else:
            raise ValueError("Cannot determine Announcement level")

        response = self.org.api.get(url)
        if response.get('featureReferences', None) is not None:
            for usage in response.get('featureReferences'):
                item = {
                    "id": usage['id'],
                    "name": usage['name'],
                    "type": usage['type'],
                    "location": self.org.locations.get(id=usage['locationId']),
                }
                if usage['type'] == 'Call Queue':
                    cq = self.org.get_call_queue_by_id(usage['id'])
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

    def replace_file(self, filename: str) -> bool:
        """ Replace the existing audio file with a new one

        Args:
            filename (str): The name of the file to replace the existing audio file with

        Returns:
            bool: True if the file was successfully replaced, False otherwise

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
            log.debug("Replacing at the Organization level")
            url = f"v1/telephony/config/announcements/{self.id}"
        elif self.level.lower() == "location":
            log.debug("Replacing at the Location level")
            url = f"v1/telephony/config/locations/{self.location['id']}/announcements/{self.id}"
        else:
            raise ValueError("Cannot determine Announcement level")

        response = self.org.api.put_upload(url, payload=encoder)

        if must_close is True:
            content.close()

        log.debug("Response:")
        log.debug(f"\t{response}")
        return True

    def delete(self) -> bool:
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
        else:
            raise ValueError("Cannot determine Announcement level")

        response = self.org.api.delete(url)
        log.debug(f"Response: {response}")
        return True


@dataclass_json
@dataclass
class Playlist:
    org: wxcadm.Org = field(repr=False)
    id: str
    """ The ID of the Playlist """
    name: str
    """ The name of the Playlist """
    file_count: int = field(metadata=config(field_name="fileCount"))
    """ The number of files in the Playlist """
    last_updated: str = field(metadata=config(field_name="lastUpdated"))
    """ The timestamp the Playlist was last updated """
    in_use: bool = field(default=False, metadata=config(field_name="isInUse"))
    """ Whether the Playlist is in use anywhere """
    location_count: int = field(default=0, metadata=config(field_name="locationCount"))
    """ The number of Locations the Playlist is associated with """

    # Attributes that will be retrieved later with a __getattr__
    file_size: int = field(init=False, repr=False, metadata=config(field_name="fileSize"))
    """ The total size of the files in the Playlist in bytes """
    announcements: list = field(init=False, repr=False)
    """ List of :class:`Announcement` instances in the Playlist """

    def __getattr__(self, item):
        # The following is a crazy fix for a PyCharm debugger bug. It serves no purpose other than to stop extra API
        # calls when developing in PyCharm. See the following bug:
        # https://youtrack.jetbrains.com/issue/PY-48306
        if item == 'shape':
            return None
        log.debug(f"Collecting details for Playlist: {self.id}")
        response = self.org.api.get("fv1/telephony/config/announcements/playlists/{self.id}")
        self.file_size = response.get('fileSize', 0)
        self.announcements = []
        for announcement in response.get('announcements', []):
            self.announcements.append(Announcement(org=self.org, **announcement))
        return self.__getattribute__(item)

    def refresh(self) -> bool:
        """ Refresh the Playlist details from the API.

        Returns:
            bool: True on success, False otherwise

        """
        response = self.org.api.get(f"v1/telephony/config/announcements/playlists/{self.id}")
        self.file_size = response.get('fileSize', 0)
        self.file_count = response.get('fileCount', 0)
        self.last_updated = response.get('lastUpdated', '')
        self.in_use = response.get('isInUse', False)
        self.location_count = response.get('locationCount', 0)
        self.announcements = []
        for announcement in response.get('announcements', []):
            self.announcements.append(Announcement(org=self.org, **announcement))
        return True

    def delete(self) -> bool:
        """ Delete the Playlist

        Returns:
            bool: True on success, False otherwise

        """
        self.org.api.delete(f"v1/telephony/config/announcements/playlists/{self.id}")
        return True

    def replace_announcements(self, announcements: list[Announcement]) -> bool:
        """ Replace the announcements in the Playlist with the given list of Announcements.

        Args:
            announcements (list[Announcement]): The list of Announcements to replace the announcements in the
                Playlist with.

        Returns:
            bool: True on success, False otherwise

        """
        payload = {'announcementIds': []}
        for announcement in announcements:
            payload['announcementIds'].append(announcement.id)
        self.org.api.put(f"v1/telephony/config/announcements/playlists/{self.id}", payload=payload)
        self.refresh()
        return True

    @property
    def locations(self) -> list[wxcadm.Location]:
        """ The list of Locations the Playlist is associated with """
        log.debug(f"Getting locations for Playlist: {self.id}")
        response = self.org.api.get(f"v1/telephony/config/announcements/playlists/{self.id}/locations")
        locations = []
        for location in response['locations']:
            if location['playlistId'] == self.id:
                locations.append(wxcadm.Location(org=self.org, **location))
        return locations

    def assign_to_location(self, location: wxcadm.Location) -> bool:
        """ Assign the Playlist to the given Location

        Args:
             location (Location): The Location to assign the Playlist to

        Returns:
            bool: True on success, False otherwise

        """
        payload = {'locationIds': []}
        current_locations = self.locations
        for current_loc in current_locations:
            payload['locationIds'].append(current_loc.id)
        payload['locationIds'].append(location.id)

        self.org.api.put(f"v1/telephony/config/announcements/playlists/{self.id}", payload=payload)
        self.refresh()
        return True


class PlaylistList(UserList):
    def __init__(self, parent: wxcadm.Org):
        super().__init__()
        self.org: wxcadm.Org = parent
        self.data: list = self._get_data()

    def _get_data(self) -> list:
        response = self.org.api.get("v1/telephony/config/announcements/playlists", items_key='playlists')
        log.debug(f"Response: {response}")
        data = []
        for item in response:
            item['org'] = self.org
            data.append(Playlist.from_dict(item))
        return data

    def get(self, id: str = '', name: str ='') -> Playlist | None:
        """ Get a :class:`Playlist` by ID or Name

        Args:
            id (str, optional): The ID of the Playlist
            name (str, optional): The Name of the Playlist

        Returns:
            Playlist: The matching :class:`Playlist`
            None: If no Playlist was found

        """
        for playlist in self.data:
            if id != '' and playlist.id == id:
                return playlist
            if name != '' and playlist.name == name:
                return playlist
        return None

    def create(self, name: str, announcements: list[Announcement]) -> Playlist:
        """ Create a new Playlist

        Args:
            name (str): The name of the Playlist
            announcements (list[Announcement]): A list of :class:`Announcement` instances to associate with the Playlist

        Returns:
            Playlist: The created Playlist

        """
        log.info(f"Creating Playlist: {name}")
        payload = {'name': name,
                   'announcementIds': []}
        for announcement in announcements:
            payload['announcementIds'].append(announcement.id)
        response = self.org.api.post(f"v1/telephony/config/announcements/playlists", payload=payload)
        new_playlist_info = self.org.api.get(f"v1/telephony/config/announcements/playlists/{response['id']}")
        new_playlist_info['org'] = self.org
        log.debug(f"Response: {new_playlist_info}")
        this_playlist = Playlist.from_dict(new_playlist_info)
        self.data.append(this_playlist)
        return this_playlist

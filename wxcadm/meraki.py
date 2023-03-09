from typing import Optional, Union

import wxcadm
from wxcadm import log
from .redsky import RedSky
import meraki


def tags_decoder(tags: list, match_string: Optional[str] = "911-") -> Optional[str]:
    """ Takes a list of tags and finds the one matching the ``match_string``

    When the match is found, it also converts underscores to spaces and returns the value without the ``match_string``.

    Args:
        tags (list): A list of tags, normally from a Meraki device
        match_string (str): A string to match to find the first tag. Defaults to ``'911-'``

    Returns:
        str: The normalized value of the matching tag.

    """
    loc_tag = None
    for tag in tags:
        if match_string in tag:
            loc_tag = tag
            break
    if loc_tag is None:
        return None
    loc_tag = loc_tag.replace(match_string, "")
    loc_tag = loc_tag.replace("_", " ")
    return loc_tag


def address_cleaner(address: str) -> str:
    clean_address = address.replace("\n", ", ")
    return clean_address


class Meraki:
    """ The top-level class for communicating with Meraki """
    def __init__(self, api_key: Optional[str] = None):
        """ Initialize a Meraki instance

        Args:
            api_key (str): The API key provided by Meraki to manage the Dashboard via API

        """

        log.info("Connecting to the Meraki Dashboard")
        self.dashboard = meraki.DashboardAPI(api_key=api_key, suppress_logging=True)
        """ The API connection to the Meraki Dashboard """
        self._orgs = []

    def get_orgs(self):
        """ Get the list of :py:class:`MerakiOrg` instances that are managed by the API token

        Returns:
            list[MerakiOrg]

        """
        log.info("Getting list of organizations from Meraki")
        org_list = self.dashboard.organizations.getOrganizations()
        log.debug(f"\t{org_list}")
        for org in org_list:
            this_org = MerakiOrg(self.dashboard, org)
            self._orgs.append(this_org)
        return self._orgs

    def get_org_by_name(self, name: str):
        """ Get the :py:class:`MerakiOrg` instance for a specific Organization name

        Args:
            name (str): The name of the Meraki Organization to get

        Returns:
            MerakiOrg: The :class:`MerakiOrg` instance

        """
        log.info(f"Getting organization with name: {name}")
        if not self._orgs:
            self.get_orgs()
        org: MerakiOrg
        for org in self._orgs:
            if org.name.upper() == name.upper():
                return org
        return None


class MerakiOrg:
    def __init__(self, dashboard: meraki.DashboardAPI, org_config: dict):
        self.dashboard = dashboard
        """ The API connection to the Meraki dashboard """
        self.id = org_config.get('id', None)
        """ The ID of the organization """
        self.name = org_config.get('name', None)
        """ The organization name """
        self._networks = []

    def get_networks(self):
        """ Get all the :class:`MerakiNetwork` instances for the Organization

        Returns:
            list[MerakiNetwork]: A list of the MerakiNetwork instances

        """
        log.info(f"Getting networks for Organization ID {self.id}")
        network_list = self.dashboard.organizations.getOrganizationNetworks(organizationId=self.id)
        log.debug(f"\t{network_list}")
        for network in network_list:
            this_network = MerakiNetwork(self.dashboard, network)
            self._networks.append(this_network)
        return self._networks

    def get_network_by_name(self, name: str):
        """ Get the :py:class:`MerakiNetwork` instance for a specified Network name

        Args:
            name (str): The Network name to get

        Returns:
            MerakiNetwork: The matching instance

        """
        log.info(f"Getting Network with name: {name}")
        if not self._networks:
            self.get_networks()
        net: MerakiNetwork
        for net in self._networks:
            if net.name.upper() == name.upper():
                return net
        return None


class MerakiNetwork:
    def __init__(self, dashboard: meraki.DashboardAPI, network_config: dict):
        self.dashboard = dashboard
        """ The API connection to the Merak Dashboard """
        self.id = network_config.get('id', None)
        """ The Network ID """
        self.name = network_config.get('name', None)
        """ The name of the Network """
        self._devices = []
        self._redsky: Optional[RedSky] = None

    def get_devices(self):
        """ Get a list of all :py:class:`MerakiDevice` instances for the Network

        Returns:
            list[MerakiDevice]: List of the MerakiDevice instances

        """
        device_list = self.dashboard.networks.getNetworkDevices(self.id)
        for device in device_list:
            if "MS" in device['model']:
                this_device = MerakiSwitch(self.dashboard, device)
            elif "MR" in device['model']:
                this_device = MerakiWireless(self.dashboard, device)
            else:
                continue
            if self._redsky is not None:
                this_device._redsky = self._redsky
            self._devices.append(this_device)
        return self._devices

    def attach_redsky(self, username: str, password: str) -> bool:
        """ Attach a :py:class:`wxcadm.RedSky` instance to the Meraki Network

        Args:
            username (str): The RedSky admin user
            password (str): The RedSky admin password

        Returns:
            bool: True on success, False otherwise

        """
        try:
            redsky_connection = RedSky(username, password)
        except wxcadm.APIError:
            return False
        self._redsky = redsky_connection
        for device in self._devices:
            device._redsky = redsky_connection
        return True

    def redsky_audit(self, simulate: bool = False):
        """ Audit the Meraki network against RedSky Horizon Mobility.

        Network devices with a tag that begins with "911-" will be used to build the RedSky Network Discovery wiremap,
        including Locations. The audit assumes that the Buildings already exist, and the address is used to match.

        Args:
            simulate (bool, optional): When set to True, no changes will be performed on the RedSky platform.
                The AuditResults will show the changes that would have been made. Defaults to False

        Returns:
            MerakiAuditResults: The results of the network audit

        """
        if self._redsky is None:
            raise RuntimeError("No RedSky instance attached")

        audit_results = MerakiAuditResults()
        device: Union[MerakiDevice, MerakiSwitch, MerakiWireless]
        for device in self.get_devices():
            log.info(f"Auditing device: {device.name}")
            device_building: wxcadm.redsky.RedSkyBuilding = device.get_redsky_building()
            if device_building is None:
                audit_results.missing_buildings.append(device.address)
                # new_building = self._redsky.add_building(address_string=device.address)
                continue

            if isinstance(device, MerakiSwitch):
                audit_results.switches.append(device)
                # Chassis
                device_location_tag = tags_decoder(device.tags)
                if device_location_tag is None:
                    log.info("No location information in Meraki. Skipping")
                    audit_results.ignored_devices.append(device)
                    continue
                # Get the RedSky Location within the building that corresponds to the location tag
                chassis_redsky_location = device_building.get_location_by_name(name=device_location_tag)
                if chassis_redsky_location is None:
                    log.info(f"No Location found for {device_location_tag} in Building {device_building.name}. Adding.")
                    if simulate is False:
                        device_building.add_location(location_name=device_location_tag,
                                                     location_info=device_location_tag)
                        chassis_redsky_location = device_building.get_location_by_name(name=device_location_tag)
                    audit_results.added_locations.append({'building': device_building, 'location': device_location_tag})

                chassis_lldp_discovery = self._redsky.get_lldp_discovery_by_chassis(chassis_id=device.mac)
                if chassis_lldp_discovery is None:
                    log.info(f"Chassis {device.mac} not in RedSky. Adding.")
                    if simulate is False:
                        self._redsky.add_lldp_discovery(chassis=device.mac,
                                                        location=chassis_redsky_location,
                                                        description=device.name)
                    audit_results.added_chassis.append(device)
                else:
                    # Check the existing LLDP discovery location against what Meraki says it should be
                    if chassis_lldp_discovery['erl']['name'] != device_location_tag:
                        log.info(f"Chassis {device.mac} has wrong location. Updating to {device_location_tag}")
                        if simulate is False:
                            self._redsky.update_lldp_location(entry_id=chassis_lldp_discovery['id'],
                                                              chassis=device.mac,
                                                              new_location=chassis_redsky_location,
                                                              description=device.name)
                        audit_results.updated_locations.append(device)


                # Ports
                port: MerakiSwitchPort
                for port in device.get_ports():
                    port_location_tag = tags_decoder(port.tags)
                    if port_location_tag is None:
                        # The port uses the chassis location. No work required
                        continue
                    port_redsky_location = device_building.get_location_by_name(name=port_location_tag)
                    if port_redsky_location is None:
                        log.info(f"No Location found for {port_location_tag} in Building {device_building.name}. "
                                 f"Adding.")
                        if simulate is False:
                            device_building.add_location(location_name=port_location_tag,
                                                         location_info=port_location_tag)
                            port_redsky_location = device_building.get_location_by_name(name=port_location_tag)
                        audit_results.added_locations.append({'building': device_building,
                                                              'location': port_location_tag})

                    chassis_lldp_discovery = self._redsky.get_lldp_discovery_by_chassis(chassis_id=device.mac)
                    # If we are in simulate mode, there may not be a chassis LLDP, so we have to fake it
                    if simulate is True:
                        chassis_lldp_discovery = {'ports': []}
                    found_port = None
                    for mapped_port in chassis_lldp_discovery['ports']:
                        if mapped_port['portId'] == port.port_id:
                            found_port = mapped_port

                    if found_port is None:
                        log.info(f"Port {port.port_id} on chassis {port.switch.mac} not in RedSky. Adding.")
                        if simulate is False:
                            self._redsky.add_lldp_discovery(chassis=port.switch.mac,
                                                            ports=[str(port.port_id)],
                                                            location=port_redsky_location,
                                                            description=port.name)
                        audit_results.added_ports.append(port)
                    else:
                        # Check the existing LLDP discovery location against what Meraki says it should be
                        if found_port['erl']['name'] != port_location_tag:
                            log.info(f"Port {device.mac}-{port.port_id} has the wrong location. "
                                     f"Updating to {port_location_tag}")
                            if simulate is False:
                                self._redsky.update_lldp_port_location(entry_id=found_port['id'],
                                                                       chassis_id=chassis_lldp_discovery['id'],
                                                                       port=str(port.port_id),
                                                                       new_location=port_redsky_location,
                                                                       description=port.name)
                            audit_results.updated_locations.append(port)
            elif isinstance(device, MerakiWireless):
                audit_results.access_points.append(device)
                device_location_tag = tags_decoder(device.tags)
                if device_location_tag is None:
                    audit_results.ignored_devices.append(device)
                    continue

                ap_redsky_location = device_building.get_location_by_name(device_location_tag)
                if ap_redsky_location is None:
                    log.info(f"No Location found for {device_location_tag} in Building {device_building.name}. Adding.")
                    if simulate is False:
                        device_building.add_location(location_name=device_location_tag, location_info=device_location_tag)
                        ap_redsky_location = device_building.get_location_by_name(device_location_tag)
                    audit_results.added_locations.append({'building': device_building, 'location': device_location_tag})

                for bss in device.get_bss_list():
                    rs_bssid_found = False
                    for bssid in self._redsky.get_bssid_discovery():
                        if bssid['bssid'].upper() == bss['bssid'].upper():
                            log.info(f"BSSID {bss['bssid']} already in RedSky")
                            rs_bssid_found = True
                    if rs_bssid_found is False:
                        log.info(f"BSSID {bss['bssid']} not in RedSky. Adding")
                        if simulate is False:
                            self._redsky.add_bssid_discovery(bssid=bss['bssid'].upper(),
                                                             location=ap_redsky_location,
                                                             description=f"{bss['ssid_name']} {bss['band']}")
                        audit_results.added_bssid.append(bss['bssid'])

        return audit_results


class MerakiDevice:
    def __init__(self, dashboard: meraki.DashboardAPI, device_config: dict):
        self.dashboard: meraki.DashboardAPI = dashboard
        """ The API connection to the Meraki Dashboard """
        self.address: str = device_config.get('address', None)
        """ The street address associated with the device """
        self.serial: str = device_config.get('serial', None)
        """ The serial number of the device """
        self.mac: str = device_config.get('mac', None)
        """ The MAC address of the device """
        self.model: str = device_config.get('model', None)
        """ The model name/number of the device """
        self.tags: list[str] = device_config.get('tags', [])
        """ Any tags associated with the device in the Meraki Dashboard """
        self.name: str = device_config.get('name', None)
        """ The name of the device """
        self._redsky: Optional[RedSky] = None
        self._redsky_building = None

    def get_redsky_building(self, redsky: Optional[RedSky] = None):
        """ Use the Meraki Device address to attempt to find the associated Building in RedSky Horizon Mobility.

        Because both addresses are unstructured, this method attempts a "best guess" by normalizing the addresses in
        both systems and trying to make a match. If no match is made, None is returned.

        In order for this method to work, either a :py:class:`wxcadm.Redsky` instance must be passed as an agument or
        the RedSky instance should be attached to the MerakiNetwork with :py:meth:`MerakiNetwork.attach_redsky()`.

        Args:
            redsky (wxcadm.RedSky, optional): The RedSky instance to use in order to call the RedSky APIs

        Returns:
            RedSkyBuilding: The :py:class:`wxcadm.redsky.RedSkyBuilding` instance. None is returned if no match is made.

        """
        if redsky is None:
            if self._redsky is not None:
                redsky = self._redsky
            else:
                raise ValueError("No RedSky instance attached")

        clean_address = address_cleaner(self.address)
        log.debug(f"Finding RedSky Building for: {clean_address}")
        for building in redsky.buildings:
            # Check the full address in Meraki to see if we have a matching Building
            if clean_address == building.address['normalizedAddress']:
                log.debug(f"Full address match: {building.address['normalizedAddress']} - {building.name}")
                self._redsky_building = building
                break
            elif clean_address.split(',')[0] == building.address['streetAddress']:
                log.debug(f"Street address match: {building.address['streetAddress']} - {building.name}")
                self._redsky_building = building
                break
        if self._redsky_building is None:
            log.error(f"No RedSky Building match for {self.address}. Ensure the building is built in RedSky")
        return self._redsky_building


class MerakiSwitch(MerakiDevice):
    def __init__(self, dashboard: meraki.DashboardAPI, device_config: dict):
        super().__init__(dashboard, device_config)
        self._port_list = []

    def get_ports(self):
        """ Get the list of ports on the Switch

        Returns:
            list[MerakiSwitchPort]: A list of :py:class:`MerakiSwitchPort` instances

        """
        port_list = self.dashboard.switch.getDeviceSwitchPorts(serial=self.serial)
        for port in port_list:
            this_port = MerakiSwitchPort(switch=self, port_id=port['portId'], **port)
            self._port_list.append(this_port)
        return self._port_list


class MerakiSwitchPort:
    def __init__(self, switch: MerakiSwitch, port_id: int, **kwargs):
        self.switch = switch
        """ The :py:class:`MerakiSwitch` the port is associated with """
        self.port_id = port_id
        """ The port number """
        self.name: str = kwargs.get('name', "")
        """ The name of the port in the Meraki Dashboard """
        self.tags: list = kwargs.get('tags', [])
        """ A list of tags for the port """
        self.enabled: bool = kwargs.get('enabled', False)
        """ Whether the port is enabled or not """
        self.type: str = kwargs.get('type', 'Unknown')
        """ The type of port """


class MerakiWireless(MerakiDevice):
    def __init__(self, dashboard: meraki.DashboardAPI, device_config: dict):
        super().__init__(dashboard, device_config)
        self._bss_list = []

    def get_bss_list(self):
        """ Get the list of all BSSIDs associated with the Access Point

        Returns:
            list[dict]: A list of the BSS in dict format

        """
        bss_list = self.dashboard.wireless.getDeviceWirelessStatus(serial=self.serial)
        for bss in bss_list['basicServiceSets']:
            if bss['enabled'] is True:
                this_bss = {
                    'bssid': bss['bssid'],
                    'ssid_name': bss['ssidName'],
                    'band': bss['band']
                }
                self._bss_list.append(this_bss)
        return self._bss_list


class MerakiAuditResults:
    def __init__(self):
        self.missing_buildings = []
        """ Buildings that were not found based on the address of the Meraki Device """
        self.added_locations = []
        """ Locations added to existing Buildings in RedSky """
        self.switches = []
        """ List of Meraki switches found in the Dashboard """
        self.access_points = []
        """ List of Meraki Access Points found in the Dashboard """
        self.added_chassis = []
        """ Chassis devices added to RedSky LLDP Discovery """
        self.added_ports = []
        """ Switch ports added to RedSky LLDP Discovery """
        self.ignored_devices = []
        """ Meraki devices that were ignored due to non-present 911 tags """
        self.updated_locations = []
        """ Locations that were uypdated from previous values """
        self.added_bssid = []
        """ BSSIDs added to RedSky BSSID Network Discovery """
        pass

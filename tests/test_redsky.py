import unittest
import os
from dotenv import load_dotenv
import wxcadm
from random import choice

class TestRedSkyConfig(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        load_dotenv()
        cls.redsky_user = os.getenv("REDSKY_USER")
        cls.redsky_pass = os.getenv("REDSKY_PASS")
        if not cls.redsky_pass or not cls.redsky_user:
            print("No REDSKY credentials found. Cannot continue.")
            exit(1)

    def setUp(self) -> None:
        self.redsky = wxcadm.RedSky(self.redsky_user, self.redsky_pass)

    def test_get_all_locations(self):
        locations = self.redsky.get_all_locations()
        self.assertIsInstance(locations, dict)
        self.assertIsInstance(locations['corporate'], list)
        self.assertIsInstance(locations['personal'], list)

    def test_buildings(self):
        buildings = self.redsky.buildings
        self.assertIsInstance(buildings, list)

    def test_held_devices(self):
        devices = self.redsky.held_devices
        self.assertIsInstance(devices, list)

    def test_phones_without_location(self):
        devices = self.redsky.phones_without_location()
        self.assertIsInstance(devices, list)

    def test_get_mac_discovery(self):
        mac = self.redsky.get_mac_discovery()
        self.assertIsInstance(mac, list)

    def test_get_lldp_discovery(self):
        lldp = self.redsky.get_lldp_discovery()
        self.assertIsInstance(lldp, list)

    def test_get_bssid_discovery(self):
        bssid = self.redsky.get_bssid_discovery()
        self.assertIsInstance(bssid, list)

    def test_get_ip_range_discovery(self):
        ip = self.redsky.get_ip_range_discovery()
        self.assertIsInstance(ip, list)


class TestRedSkyUsers(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        load_dotenv()
        cls.redsky_user = os.getenv("REDSKY_USER")
        cls.redsky_pass = os.getenv("REDSKY_PASS")
        if not cls.redsky_pass or not cls.redsky_user:
            print("No REDSKY credentials found. Cannot continue.")
            exit(1)

    def setUp(self) -> None:
        self.redsky = wxcadm.RedSky(self.redsky_user, self.redsky_pass)

    def test_get_users(self):
        userlist = self.redsky.users
        self.assertIsInstance(userlist, wxcadm.redsky.RedSkyUsers)


class TestRedSkyBuilding(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        load_dotenv()
        cls.redsky_user = os.getenv("REDSKY_USER")
        cls.redsky_pass = os.getenv("REDSKY_PASS")
        if not cls.redsky_pass or not cls.redsky_user:
            print("No REDSKY credentials found. Cannot continue.")
            exit(1)

    def setUp(self) -> None:
        self.redsky = wxcadm.RedSky(self.redsky_user, self.redsky_pass)

    def test_get_building(self):
        building = choice(self.redsky.buildings)
        self.assertIsInstance(building, wxcadm.redsky.RedSkyBuilding)
        with self.subTest("Building Locations"):
            locations = building.locations
            self.assertIsInstance(locations, list)
            self.assertIsInstance(locations[0], wxcadm.redsky.RedSkyLocation)

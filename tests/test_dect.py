import unittest
import os
from dotenv import load_dotenv
import wxcadm
from random import choice, randint


class TestDectDataPull(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        load_dotenv()
        cls.access_token = os.getenv("WEBEX_ACCESS_TOKEN")
        if not cls.access_token:
            print("No WEBEX_ACCESS_TOKEN found. Cannot continue.")
            exit(1)

    def setUp(self) -> None:
        self.webex = wxcadm.Webex(self.access_token)
        self.random_location = choice(self.webex.org.locations.webex_calling())

    def test_dect_networks(self) -> None:
        org_dect_network = self.webex.org.dect_networks
        self.assertIsInstance(org_dect_network, wxcadm.dect.DECTNetworkList)
        if len(org_dect_network) > 0:
            self.assertIsInstance(org_dect_network[0], wxcadm.dect.DECTNetwork)
            with self.subTest('Location-based .dect_networks'):
                location = self.webex.org.locations.get(id=org_dect_network[0].location_id)
                self.assertIsInstance(location.dect_networks, wxcadm.dect.DECTNetworkList)
                self.assertIsInstance(location.dect_networks[0], wxcadm.dect.DECTNetwork)

    def test_dect_base_stations(self) -> None:
        org_dect_network = self.webex.org.dect_networks
        if len(org_dect_network) == 0:
            self.skipTest('No DECT Networks')
        self.assertIsInstance(org_dect_network.with_base_stations(), list)
        if len(org_dect_network.with_base_stations()) == 0:
            self.skipTest("No Base Stations")
        network = org_dect_network.with_base_stations()[0]
        self.assertIsInstance(network, wxcadm.dect.DECTNetwork)
        self.assertIsInstance(network.base_stations, list)
        base_station = network.base_stations[0]
        self.assertIsInstance(base_station, wxcadm.dect.DECTBaseStation)
        self.assertIsInstance(base_station.id, str)
        self.assertIsInstance(base_station.mac, str)
        self.assertIsInstance(base_station.number_of_lines_registered, int)

    def test_dect_handsets(self) -> None:
        org_dect_network = self.webex.org.dect_networks
        if len(org_dect_network) == 0:
            self.skipTest('No DECT Networks')
        self.assertIsInstance(org_dect_network.with_base_stations(), list)
        if len(org_dect_network.with_base_stations()) == 0:
            self.skipTest("No Base Stations")
        network = org_dect_network.with_base_stations()[0]
        self.assertIsInstance(network, wxcadm.dect.DECTNetwork)
        self.assertIsInstance(network.handsets, list)
        if len(network.handsets) == 0:
            self.skipTest("No Handsets")
        handset = network.handsets[0]
        self.assertIsInstance(handset, wxcadm.dect.DECTHandset)
        self.assertIsInstance(handset.id, str)
        self.assertEqual(handset.dect_network, network)
        self.assertIsInstance(handset.lines, list)
        line = handset.lines[0]
        self.assertIsInstance(line['memberId'], str)


class TestDectBuildAndRemove(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        load_dotenv()
        cls.access_token = os.getenv("WEBEX_ACCESS_TOKEN")
        if not cls.access_token:
            print("No WEBEX_ACCESS_TOKEN found. Cannot continue.")
            exit(1)

    def setUp(self) -> None:
        self.webex = wxcadm.Webex(self.access_token)
        self.random_location = choice(self.webex.org.locations.webex_calling())

    def test_full_build(self) -> None:
        with self.subTest("Create DECT Network"):
            new_network = self.webex.org.dect_networks.create(
                'wxcadm Test Network',
                'DBS210',
                location=self.random_location
            )
            self.assertIsInstance(new_network, wxcadm.dect.DECTNetwork)
        with self.subTest("Create Base Station"):
            bs_mac_addr: str = "020000%02x%02x%02x" % (randint(0, 255),
                                                       randint(0, 255),
                                                       randint(0, 255))
            base_stations = new_network.add_base_stations(mac_list=[bs_mac_addr])
            self.assertIsInstance(base_stations, list)
            self.assertIsInstance(base_stations[0], wxcadm.dect.DECTBaseStation)
        with self.subTest("Add Handset"):
            person = choice(self.webex.org.people.webex_calling())
            success = new_network.add_handset('wxcadm', line1=person)
            self.assertTrue(success)
        with self.subTest("Delete Handset"):
            for handset in new_network.handsets:
                new_network.delete_handset(handset)
            self.assertIs(len(new_network.handsets), 0)
        with self.subTest("Delete Base Station"):
            for base in new_network.base_stations:
                new_network.delete_base_station(base)
            self.assertIs(len(new_network.base_stations), 0)
        with self.subTest('Delete DECT Network'):
            success = new_network.delete()
            self.assertTrue(success)



if __name__ == '__main__':
    unittest.main()

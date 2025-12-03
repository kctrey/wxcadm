import unittest
import os
from dotenv import load_dotenv
import wxcadm
from random import choice


class TestWorkspaceBargeInSettings(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        load_dotenv()
        cls.access_token = os.getenv("WEBEX_ACCESS_TOKEN")
        if not cls.access_token:
            print("No WEBEX_ACCESS_TOKEN found. Cannot continue.")
            exit(1)

    def setUp(self) -> None:
        self.webex = wxcadm.Webex(self.access_token)
        if len(self.webex.org.workspaces.professional()) == 0:
            self.skipTest(
                "No Professional Workspace available. Cannot run tests that require a professional workspace."
            )
        self.random_workspace = choice(self.webex.org.workspaces.professional())

    def test_barge_in_settings(self) -> None:
        barge_in_settings = self.random_workspace.barge_in
        self.assertIsInstance(barge_in_settings, wxcadm.workspace.BargeInSettings)

    def test_barge_in_settings_update(self) -> None:
        barge_in_settings: wxcadm.BargeInSettings = self.random_workspace.barge_in
        success = barge_in_settings.set_enabled(enabled=bool(not barge_in_settings.enabled))
        self.assertTrue(success)
        success = barge_in_settings.set_enabled(enabled=bool(barge_in_settings.enabled))
        self.assertTrue(success)




class TestWorkspaces(unittest.TestCase):
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

    def test_workspace_list(self):
        workspace_list = self.webex.org.workspaces
        self.assertIsInstance(workspace_list, wxcadm.workspace.WorkspaceList)

    def test_workspace_add_delete(self):
        with self.subTest("Workspace Add"):
            workspace_list: wxcadm.workspace.WorkspaceList = self.webex.org.workspaces
            test_location = choice(self.webex.org.locations.webex_calling())
            new_workspace = workspace_list.create(location=test_location,
                                                  name="wxcadm API Test",
                                                  capacity=1,
                                                  extension="53553",
                                                  notes="Created by wxcadm unit tests")
            self.assertIsInstance(new_workspace, wxcadm.workspace.Workspace)
            self.assertIsNotNone(new_workspace.id)

        with self.subTest("Workspace Delete"):
            new_workspace.delete()
            self.webex.org.workspaces.refresh()
            deleted_workspace = self.webex.org.workspaces.get_by_id(new_workspace.id)
            self.assertIsNone(deleted_workspace)

    def test_location_workspace_list(self):
        workspace_list = self.random_location.workspaces
        self.assertIsInstance(workspace_list, wxcadm.workspace.WorkspaceList)


if __name__ == '__main__':
    unittest.main()

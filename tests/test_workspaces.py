import unittest
import os
from dotenv import load_dotenv
import wxcadm
from random import choice

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

        with self.subTest("Workspace Delete"):
            new_workspace.delete()
            deleted_workspace = self.webex.org.workspaces.get_by_id(new_workspace.id)
            self.assertEqual(deleted_workspace, None)


if __name__ == '__main__':
    unittest.main()

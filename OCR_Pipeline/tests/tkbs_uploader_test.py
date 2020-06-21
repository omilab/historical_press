import unittest
import tkbs_uploader as up
from unittest.mock import patch
import os

#change it with your details
test_conf_parameters = ["userr@gmail.com", "password", os.path.join("resources_for_tests", "step2"),
                        "collec_id_with_permmisions, "YES", 23005, "test_dest"]


class GetCommunicationDetailsFromUser(unittest.TestCase):
    def test_set_username(self):
        with patch('builtins.input', return_value="username"):
            self.assertEqual(up.set_username(), "username")

    def test_set_password(self):
        with patch('builtins.input', return_value="pass"):
            self.assertEqual(up.set_password(), "pass")

    def test_set_collection_id(self):
        with patch('builtins.input', return_value="123"):
            self.assertEqual(up.set_collection_id(), "123")

    def test_set_line_detection_id(self):
        with patch('builtins.input', return_value="pass"):
            self.assertEqual(up.set_line_detection_id(), "pass")

    def test_set_htr_model_id(self):
        with patch('builtins.input', return_value="pass"):
            self.assertEqual(up.set_htr_model_id(), "pass")


class GetPathFromUser(unittest.TestCase):
    def test_get_empty_path_from_user(self):
        with patch('builtins.input', return_value=""):
            self.assertEqual(up.set_source_path(), os.path.dirname(__file__))

        with patch('builtins.input', return_value="    "):
            self.assertEqual(up.set_source_path(), os.path.dirname(__file__))

    def test_get_illegal_path_from_user(self):
        with patch('builtins.input', side_effect=['123456789', 'bar', '']):
            self.assertEqual(up.set_source_path(), os.path.dirname(__file__))

    def test_get_absolute_path_from_user(self):
        work_dir = os.path.dirname(__file__)
        abs_path = os.path.join(work_dir, "resources_for_tests")
        with patch('builtins.input',
                   return_value=abs_path):
            self.assertEqual(up.set_source_path(), abs_path)

    def test_get_relative_path_from_user(self):
        with patch('builtins.input',
                   return_value="resources_for_tests"):
            work_dir = os.path.dirname(__file__)
            self.assertEqual(up.set_source_path(),
                             os.path.join(work_dir, "resources_for_tests"))


class ExtractStructureJsonFromTOCFile(unittest.TestCase):
    def test_structure_json_str_extraction_from_toc(self):
        json_string = """{"md": {"title": "021-HZF-1914-11-06-001-400797", "author": "test_user", "description": "pipeline"}, "pageList": {"pages": [{"fileName": "Pg001_144.png", "pageXmlName": "Pg001_144.pxml", "pageNr": 1}, {"fileName": "Pg002_144.png", "pageXmlName": "Pg002_144.pxml", "pageNr": 2}, {"fileName": "Pg003_144.png", "pageXmlName": "Pg003_144.pxml", "pageNr": 3}, {"fileName": "Pg004_144.png", "pageXmlName": "Pg004_144.pxml", "pageNr": 4}]}}"""

        self.assertEqual(up.extract_json_for_tkbs_from_toc_file()[0], json_string)

    def test_list_of_images_and_xml_extraction_from_toc(self):
        # print(up.extract_json_for_tkbs_from_toc_file()[1])
        pass


class UploadFileIntoTranskribus(unittest.TestCase):
    def test_file_uploader(self):
        config = up.Config(test_conf_parameters)
        tkbs_client = up.connect_to_tkbs(config)
        json_as_str, img_and_xml_list = up.extract_json_for_tkbs_from_toc_file()
        docid = up.upload(67217, tkbs_client, json_as_str, img_and_xml_list, )
        print(docid)


class DownloadFileFromTranskribus(unittest.TestCase):
    def test_file_downloader(self):
        config = up.Config(test_conf_parameters)
        tkbs_client = up.connect_to_tkbs(config)
        collec = 67217
        docid = "384626"
        response = up.download(collec, docid, "dowload_test", tkbs_client)
        print(response)


class UploadPipline(unittest.TestCase):
    def test_upload_pipeline(self):
        config = up.Config(test_conf_parameters)
        up.upload_pipeline(config)


class HelperFunctions(unittest.TestCase):
    def test_remove_directory(self):
        path = "/test_remove_directory"
        try:
            os.mkdir(path)
        except OSError:
            print("Creation of the directory %s failed" % path)

        before_remove = os.path.isdir(path)
        after_remove = up.delete_directory(path)
        self.assertNotEqual(before_remove, after_remove)

    def test_extract_title_from_xml(self):
        toc_path = "data/1920-01-06/TOC.xml"
        self.assertEqual(up.extract_title_from_TOC_xml(toc_path), "021-HZF-1920-01-06-001-4600015")

    def test_get_config_from_json(self):
        config = up.Config()
        # TODO: json file for that test


if __name__ == '__main__':
    unittest.main()

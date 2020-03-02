# For these test you need the files in the folder "resources_for_tests"

import unittest
from unittest.mock import patch
import os

import legacy_to_tkbs_format_converter as fc


class MyTestCase(unittest.TestCase):
    def test_something(self):
        self.assertEqual(True, True)


class InputFromUser(unittest.TestCase):
    def test_get_empty_path_from_user(self):
        with patch('builtins.input', return_value=""):
            self.assertEqual(fc.get_path_from_user(), os.path.dirname(__file__))

        with patch('builtins.input', return_value="    "):
            self.assertEqual(fc.get_path_from_user(), os.path.dirname(__file__))


    def test_get_illegal_path_from_user(self):
        with patch('builtins.input', return_value="123456789"):
            self.assertEqual(fc.get_path_from_user(), "")

    def test_get_absolute_path_from_user(self):
        work_dir = os.path.dirname(__file__)
        abs_path = os.path.join(work_dir, "resources_for_tests")
        with patch('builtins.input',
                   return_value=abs_path):
            self.assertEqual(fc.get_path_from_user(), abs_path)

    def test_get_relative_path_from_user(self):
        with patch('builtins.input',
                   return_value="resources_for_tests"):
            work_dir = os.path.dirname(__file__)
            self.assertEqual(fc.get_path_from_user(),
                             os.path.join(work_dir, "resources_for_tests"))


class PathTraverse(unittest.TestCase):
    def test_find_sub_folders_with_toc_file_empty_case(self):
        # path1 and path3 contain toc.xmk file into them
        work_dir = os.path.dirname(__file__)
        relative_path0 = "resources_for_tests\\1920-01-06\\Document\\1\\Img"
        path0 = os.path.join(work_dir, relative_path0)
        self.assertEqual(fc.find_sub_folders_with_toc_file(path0), [])

    def test_find_sub_folders_with_toc_file_one_folder_case(self):
        work_dir = os.path.dirname(__file__)
        relative_path1 = "resources_for_tests\\1920-01-06"
        path1 = os.path.join(work_dir, relative_path1)
        self.assertEqual(fc.find_sub_folders_with_toc_file(path1), [path1])

    def test_find_sub_folders_with_toc_file_multi_folder_case(self):
        work_dir = os.path.dirname(__file__)
        relative_parent_path = "resources_for_tests"
        parent_path = os.path.join(work_dir, relative_parent_path)
        relative_sub_folder1_path = "resources_for_tests\\1920-01-06"
        sub_folder1_path = os.path.join(work_dir, relative_sub_folder1_path)
        relative_sub_folder2_path = "resources_for_tests\\1914-11-06"
        sub_folder2_path = os.path.join(work_dir, relative_sub_folder2_path)
        self.assertEqual(set(fc.find_sub_folders_with_toc_file(parent_path)), {sub_folder1_path, sub_folder2_path})


class CreateOutputDirectory(unittest.TestCase):
    def subfolders_counter(self, src_path):
        files, folders = 0, 0
        for _, dirnames, filenames in os.walk(src_path):
            files += len(filenames)
            folders += len(dirnames)
        return folders

    def test_create_unique_output_folder(self):
        work_dir = os.path.dirname(__file__)
        relative_path = "resources_for_tests"
        src_path = os.path.join(work_dir, relative_path)
        before_adding_output_folder = self.subfolders_counter(src_path)
        output_folder = fc.create_unique_output_folder(src_path)
        after_adding_output_folder = self.subfolders_counter(src_path)
        self.assertEqual(before_adding_output_folder + 1, after_adding_output_folder)
        # test_create_sub_folder_in_output_folder_for_every_sub_folder_with_toc_file
        folders_to_be_converted = fc.find_sub_folders_with_toc_file(src_path)
        num_of_toc_files = len(folders_to_be_converted)
        before_adding_output_sub_folders = self.subfolders_counter(src_path)
        fc.create_sub_folders_in_output_folder(output_folder, folders_to_be_converted)
        after_adding_output_sub_folders = self.subfolders_counter(src_path)
        self.assertEqual(before_adding_output_sub_folders + num_of_toc_files, after_adding_output_sub_folders)


class ConvertFormatFile(unittest.TestCase):
    def test_something(self):
        pass


if __name__ == '__main__':
    unittest.main()

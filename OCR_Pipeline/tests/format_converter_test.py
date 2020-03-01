#  For these test you need the paths like they appear below or change them for your directory. 


import unittest
from unittest.mock import patch
import os

import legacy_to_tkbs_format_converter as fc


class MyTestCase(unittest.TestCase):
    def test_something(self):
        self.assertEqual(True, True)


class InputFromUser(unittest.TestCase):
    def test_get_path_from_user(self):
        with patch('builtins.input', return_value=""):
            self.assertEqual(fc.get_path_from_user(), "")

        with patch('builtins.input', return_value="no"):
            self.assertEqual(fc.get_path_from_user(), "")

        with patch('builtins.input',
                   return_value="C:\\Users\\User\\Documents\\Projects\\OmiLab\\new pipeline\\data\\1914-11-06-TEST\\output"):
            self.assertEqual(fc.get_path_from_user(),
                             "C:\\Users\\User\\Documents\\Projects\\OmiLab\\new pipeline\\data\\1914-11-06-TEST\\output")


class PathTraverse(unittest.TestCase):
    def test_find_sub_folders_with_toc_file(self):
        # path1 and path3 contain toc.xmk file into them
        path0 = "C:\\Users\\User\\Documents\\Projects\\OmiLab\\new pipeline\\data\\1914-11-06-TEST\\output"
        self.assertEqual(fc.find_sub_folders_with_toc_file(path0), [])
        path1 = "C:\\Users\\User\\Documents\\Projects\\OmiLab\\new pipeline\\data\\1914-11-06-TEST"
        self.assertEqual(fc.find_sub_folders_with_toc_file(path1), [path1])
        path2 = "C:\\Users\\User\\Documents\\Projects\\OmiLab\\new pipeline\\data"
        path3 = "C:\\Users\\User\\Documents\\Projects\\OmiLab\\new pipeline\\data\\1920-01-06"
        self.assertEqual(set(fc.find_sub_folders_with_toc_file(path2)), {path1, path3})


class CreateOutputDirectory(unittest.TestCase):
    def subfolders_counter(self, src_path):
        files, folders = 0, 0
        for _, dirnames, filenames in os.walk(src_path):
            files += len(filenames)
            folders += len(dirnames)
        return folders

    def test_create_unique_output_folder(self):
        src_path = "C:\\Users\\User\\Documents\\Projects\\OmiLab\\new pipeline\\data"
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

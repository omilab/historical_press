import os
import datetime
from TkbsDocument import Document


def get_path_from_user():
    user_input = input("Enter the path of your files (or press Enter for current folder): ")
    if user_input.strip() == "":  # Check for empty string
        return os.path.dirname(__file__)
    if os.path.isabs(user_input):  # Check if the input is absolute path or relative
        dir_name = user_input
    else:
        work_dir = os.path.dirname(__file__)
        dir_name = os.path.join(work_dir, user_input)
    if os.path.isdir(dir_name):
        return dir_name
    else:
        print("Illegal path, try again")
        return ""


def find_sub_folders_with_toc_file(dir_path):  # Get absolute path
    sub_folders_with_TOC_file = []
    for subdir, dirs, files in os.walk(dir_path):
        for file in files:
            if file == "TOC.xml":
                sub_folders_with_TOC_file.append(subdir)
    return sub_folders_with_TOC_file


def create_unique_output_folder(dir_path):
    start_time = str(datetime.datetime.now().strftime("%y-%m-%d_%H-%M-%S"))
    output_path = os.path.join(dir_path, "output " + start_time)
    os.mkdir(output_path)
    return output_path


def create_sub_folders_in_output_folder(output_dir_path, folders_to_be_converted):
    output_sub_folders = []
    for folder in folders_to_be_converted:
        folder_name = os.path.basename(os.path.normpath(folder))
        output_sub_folder_path = os.path.join(output_dir_path, folder_name)
        os.mkdir(output_sub_folder_path)
        output_sub_folders.append(output_sub_folder_path)
    return output_sub_folders


def convert_legacy_folder_to_tkbs_format(src_path, dst_path):
    p = Document()
    p.load_legacy_data(src_path)
    p.export_tkbs_format(dst_path)


def main():
    path = get_path_from_user()  # Path should be include TOC.xml file(s) anywhere.
    while path == "":
        path = get_path_from_user()

    folders_to_be_converted = find_sub_folders_with_toc_file(path)
    output_dir = create_unique_output_folder(path)
    output_sub_folders = create_sub_folders_in_output_folder(output_dir, folders_to_be_converted)

    for f in range(len(
            folders_to_be_converted)):  # The routine that take source folder and convert files into destination file
        convert_legacy_folder_to_tkbs_format(folders_to_be_converted[f], output_sub_folders[f])

    print("{} files converted successfully from legacy format to Transkribus format.\n"
          " You can find them now in {}'.".format(len(folders_to_be_converted), output_dir))


if __name__ == '__main__':
    main()

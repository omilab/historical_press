import json
import os
import shutil
import time
import traceback
import xml.etree.cElementTree as ET
from datetime import datetime
from xml.etree import ElementTree

from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

from TkbsApiClient import TranskribusClient
from TkbsDocument import Document


class Config:
    def __init__(self, config_parameters=None):
        if os.path.isfile('conf.json'):
            with open('conf.json') as json_file:
                conf_json = json.load(json_file)
            self.username = conf_json["username"]
            self.password = conf_json["password"]
            self.src_path = conf_json["src_path"]
            self.collection_id = conf_json["collection_id"]
            self.htr_model_id = conf_json["htr_model_id"]
            self.dst_path = conf_json["dst_path"]
            self.line_detection = conf_json["line_detection"]
        elif config_parameters is None:
            self.username = set_username()
            self.password = set_password()
            self.src_path = set_source_path()
            self.collection_id = set_collection_id()
            self.line_detection = set_line_detection_id()
            self.htr_model_id = set_htr_model_id()
            self.dst_path = set_source_path()
        else:
            self.username, self.password, self.src_path, self.collection_id, self.line_detection, self.htr_model_id, \
            self.dst_path = config_parameters

        # print(self.username, self.password, self.src_path, self.collection_id, self.htr_model_id, self.dst_path)


def set_username():
    username = input("Enter your Transkribus username: ")
    return str(username)


def set_password():
    password = input("Enter your Transkribus password: ")
    return str(password)


def set_source_path():
    user_input = input("Enter the source path of your files (or press Enter for current folder): ")
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
        return set_source_path()


def set_destination_path():
    user_input = input("Enter the destination path of your files (or press Enter if you don't want to download): ")
    if user_input.strip() == "":  # Check for empty string
        return ""
    if os.path.isabs(user_input):  # Check if the input is absolute path or relative
        dir_name = user_input
    else:
        work_dir = os.path.dirname(__file__)
        dir_name = os.path.join(work_dir, user_input)
    if os.path.isdir(dir_name):
        return dir_name
    else:
        print("Illegal path, try again")
        return set_destination_path


def set_collection_id():
    collection_id = input("Enter your collection id: ")
    return str(collection_id)


def set_line_detection_id():
    line_detection_id = input("Enter something if you want line detection (or press Enter if you don't want): ")
    return "YES" if line_detection_id != "" else ""


def set_htr_model_id():
    htr_model_id = input("Enter your HTR model id (or press Enter if you don't want text recognition): ")
    return str(htr_model_id)


def connect_to_tkbs(config):
    try:
        disable_warnings(InsecureRequestWarning)
        tkbs_client = TranskribusClient(sServerUrl="https://transkribus.eu/TrpServer")
        connection = tkbs_client.auth_login(config.username, config.password, True)
        return tkbs_client

    except Exception as e:
        print("Error: %s." % e)


def extract_json_for_tkbs_from_toc_file(toc_folder_path="resources_for_tests\\1914-11-06",
                                        images_and_xmls_folder_path="resources_for_tests\\output\\1914-11-06",
                                        author="test_user", description="pipeline"):
    p = Document()
    p.load_legacy_data(os.path.join(toc_folder_path))
    page_images, page_xmls = p.img_names_by_pgnum(), p.pxml_names_by_pgnum()
    title = extract_title_from_TOC_xml(os.path.join(toc_folder_path, "TOC.xml"))
    img_objects = {}

    for key, value in page_images.items():
        with open(os.path.join(images_and_xmls_folder_path, value), 'rb') as file:
            img_objects[key] = file.read()

    xml_objects = {}
    for key, value in page_xmls.items():
        with open(os.path.join(images_and_xmls_folder_path, value), 'rb') as file:
            xml_objects[key] = file.read()

    d = {"md": {"title": title, "author": author, "description": description},
         "pageList": {"pages": [{"fileName": value, "pageXmlName": page_xmls[
             key], "pageNr": int(key)} for key, value in page_images.items()]}}

    json_as_str = json.dumps(d)

    img_and_xml_list = [{'img': (value, img_objects[key], 'application/octet-stream'),
                         'xml': (page_xmls[key], xml_objects[key], 'application/octet-stream')} for key, value in
                        page_images.items()]
    return json_as_str, img_and_xml_list


def upload(collection_id, tkbs_client, json_as_str, img_and_xml_list, config=None):
    try:
        response = tkbs_client.createDocFromImages(collection_id, json_as_str, img_and_xml_list)
        tree = ElementTree.fromstring(response)
        total_pages = tree.find('nrOfPagesTotal').text
        document_id = tree.find('uploadId').text
        job_id = tree.find('jobId').text
        actual_uploaded_counter = 0
        pages = tree.find('pageList')
        for p in pages.findall('pages'):
            if p.find('pageUploaded').text == "true":
                actual_uploaded_counter += 1
        if actual_uploaded_counter == int(total_pages) and wait_for_job_status(job_id, 30, tkbs_client):
            # print(total + " file uploads finished successfuly")
            return int(document_id)
        else:
            print(f"ERROR - only{str(actual_uploaded_counter)} pages of {str(total_pages)} uploaded successfully.")
            return -1

    except Exception as e:
        print("Error: %s." % e)


def line_detection(collection_id, document_id, tkbs_client, config=None):
    try:
        doc_parts = '{"docList" : {"docs" : [ {"docId" : ' + str(document_id) + '}]}}'
        response = tkbs_client.analyzeLayout(colId=collection_id, docPagesJson=doc_parts, bBlockSeg=False,
                                             bLineSeg=True)
        tree = ElementTree.fromstring(response)
        status = tree.find('trpJobStatus')
        job_id = status.find('jobId').text
        seconds = 120
        return wait_for_job_status(job_id, seconds, tkbs_client, 5)
    except Exception as e:
        print("Error: %s." % e)


def run_ocr(collection_id, HTR_model_id, dictionary_name, document_id, tkbs_client, config=None):
    try:
        page_ids = get_page_ids_from_document_id(collection_id, document_id, tkbs_client)
        json_string = create_json_for_request(document_id, page_ids)
        # print(json_string)

        job_id = tkbs_client.htrRnnDecode(collection_id, HTR_model_id, dictionary_name, document_id, json_string,
                                          bDictTemp=False)
        seconds = 80 * len(page_ids)
        return wait_for_job_status(job_id, seconds, tkbs_client, 5)
    except Exception as e:
        print("ERROR in run_ocr for docid " + str(document_id))
        print(e)
        print("END ERROR \n\n")
        pass


def download(collection_id, document_id, target_folder, tkbs_client, config=None):
    print("Downloading...")
    try:
        os.makedirs(target_folder, exist_ok=True)
        print(target_folder)
        response = tkbs_client.download_document(collection_id, document_id, target_folder)
        print(response)
        time.sleep(60)
        return response

    except Exception as e:
        delete_directory(target_folder)
        print("ERROR in download")
        traceback.print_exc()
        print("Error: %s." % e)
        print(type(e))
        print(e.args)
        print("END ERROR \n\n")
        pass


def delete_directory(folder_path):
    try:
        shutil.rmtree(folder_path)
    except OSError as e:
        print("Error: %s - %s." % (e.filename, e.strerror))


def read_tkbs_json_file(trp_json_path):
    with open(trp_json_path) as f:
        data = json.load(f)
        # print(data)
        return data


def create_json_for_request(document_id, page_ids):
    d = {"docId": int(document_id), "pageList": {"pages": [{"pageId": pid} for pid in page_ids.values()]}}
    json_string = json.dumps(d)
    return json_string


def find_sub_folders_with_toc_file(dir_path):  # Get absolute path
    sub_folders_with_TOC_file = []
    for subdir, dirs, files in os.walk(dir_path):
        for file in files:
            if file == "TOC.xml":
                sub_folders_with_TOC_file.append(subdir)
    return sub_folders_with_TOC_file


def extract_title_from_TOC_xml(TOC_path):
    tree = ET.parse(TOC_path)
    root = tree.getroot()
    source = {}
    for s in root.iter('Link'):
        source = s.attrib
    if source == {}:
        title = "unknown title"
    else:
        title = (source["SOURCE"])[:-4]
    return title


def get_page_ids_from_document_id(collection_id, document_id, tkbs_client):
    # This function is slow because it requires downloading the file from Transkribus.
    # I couldn't find a way to extract the page ids without downloading the file.
    # If there is such a way - it will surely improve the running speed of the code.
    now = datetime.now()
    current_time = now.strftime("%H-%M-%S")
    temp_folder_name = "temp_folder_for_page_id_" + current_time
    download(collection_id, document_id, temp_folder_name, tkbs_client)
    trp_json_path = os.path.join(temp_folder_name, "trp.json")
    data = read_tkbs_json_file(trp_json_path)
    p = Document()
    page_ids = p.load_tkbs_page_ids(data)
    delete_directory(temp_folder_name)
    return page_ids


def upload_pipeline(config):
    p = Document()
    folders_to_be_uploaded = find_sub_folders_with_toc_file(config.src_path)

    for folder in folders_to_be_uploaded:
        tkbs_client = connect_to_tkbs(config)
        # output_folder is the folder that legacy_to_tkbs_converter save the output of this folder
        converter_output_folder = os.path.join(config.src_path, "output", os.path.basename(os.path.normpath(folder)))
        print(converter_output_folder)
        json_as_str, img_and_xml_list = extract_json_for_tkbs_from_toc_file(toc_folder_path=folder,
                                                                            images_and_xmls_folder_path=converter_output_folder,
                                                                            author=config.username,
                                                                            description="pipeline")
        document_id = upload(config.collection_id, tkbs_client, json_as_str, img_and_xml_list, config)
        print("0")
        """
        if True:  # TODO: add condition for check if line detection needed
            detection_status = line_detection(config.collection_id, document_id, tkbs_client, config)
            if not detection_status:
                print("ERROR - document failed line detection " + p.title)
                continue
        """
        print("1")
        """
        if config.htr_model_id != "":
            run_ocr(config.collection_id, config.htr_model_id, "", document_id, tkbs_client, config)
        """
        print("2")
        if config.dst_path != "":
            dest_folder = os.path.join(config.dst_path, "output", os.path.basename(os.path.normpath(folder)))
            print(dest_folder)
            download(config.collection_id, document_id, dest_folder, tkbs_client, config)
        print("3")
        time.sleep(40)


def wait_for_job_status(job_id, wait_time_in_seconds, tkbs_client, attempts=2):
    try:
        attempts_counter = 0
        while attempts_counter < attempts:
            curr_wait_time_in_seconds = wait_time_in_seconds * (1.5 ** attempts_counter)  # sleeping time increase
            attempts_counter += 1
            if wait_time_in_seconds > 0:
                print("waiting " + str(curr_wait_time_in_seconds) + ", while checking job_id " + str(job_id))
                time.sleep(curr_wait_time_in_seconds)
                # tkbs_client = connect_to_tkbs(config) TODO: re-connection after sleeping time
            response = tkbs_client.getJobStatus(str(job_id))
            if response['state'] == 'FINISHED':
                return response['success']
            else:
                if attempts_counter == attempts:
                    return False
    except Exception as e:
        print("Error: %s." % e)


def main():
    config = Config()
    upload_pipeline(config)


if __name__ == '__main__':
    main()

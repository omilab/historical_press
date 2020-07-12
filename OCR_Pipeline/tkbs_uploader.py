import json
import os
import shutil
import time
import traceback
import xml.etree.cElementTree as ET
import datetime
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
            #self.dst_path = conf_json["dst_path"]
            self.line_detection = conf_json["line_detection"]
        elif config_parameters is None:
            self.username = set_username()
            self.password = set_password()
            self.src_path = set_source_path()
            self.collection_id = set_collection_id()
            self.line_detection = set_line_detection_id()
            self.htr_model_id = set_htr_model_id()
            #self.dst_path = set_source_path()
        else:
            self.username, self.password, self.src_path, self.collection_id, self.line_detection, self.htr_model_id = config_parameters

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


def upload(collection, input_folder, pageImages, pageXmls, title, author, description, mytkbs):
    try:
        ImgObjects = {}
        for key, value in pageImages.items():
            ImgObjects[key] = open(os.path.join(input_folder, value), 'rb')
        XmlObjects = {}
        for key, value in pageXmls.items():
            XmlObjects[key] = open(os.path.join(input_folder, value), 'rb')
        pfiles = []
        jstring = '{"md": {"title": "' + title + '", "author": "' + author + '", "description": "' + description + '"}, "pageList": {"pages": ['
        psik = ', '
        for key, value in pageImages.items():
            if len(pageImages) <= int(key):
                psik = ''
            jstring = jstring + '{"fileName": "' + value + '", "pageXmlName": "' + pageXmls[key] + '", "pageNr": ' + key + '}' + psik
            pfiles.append({'img': (value, ImgObjects[key], 'application/octet-stream'), 'xml': (pageXmls[key], XmlObjects[key], 'application/octet-stream')})
        jstring = jstring + ']}}'
        response = mytkbs.createDocFromImages(collection, jstring, pfiles)
        tree = ElementTree.fromstring(response)
        total = tree.find('nrOfPagesTotal').text
        docid = tree.find('uploadId').text
        jobid = tree.find('jobId').text
        count = 0
        pages = tree.find('pageList')
        for p in pages.findall('pages'):
            pageUploaded = p.find('pageUploaded')
            if pageUploaded.text == "true":
                count +=  1
        if count == int(total) and wait_for_jobstatus(jobid, 30, mytkbs):
            #print(total + " file uploads finished successfuly")
            return int(docid)
        else:
            print("ERROR - " + str(count) + " files of " + total + " completed.")
            return -1
    except Exception as e:
                print("ERROR in upload ")
                print (e)
                print ("END ERROR \n\n")
                pass



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

def run_ocr(collection, HTRmodelid, dictionaryName, mydocid, pids, mytkbs):
    try:
        jstring = '{"docId" : ' + str(mydocid) + ', "pageList" : {"pages" : ['
        psik = ', '
        total = len(pids)
        count = 0
        for pnum, pid in pids.items():
            count += 1
            if count == total:
                psik = ''
            jstring = jstring + '{"pageId" : ' + str(pid) + '}' + psik
        jstring = jstring + ']}}'
        jobid = mytkbs.htrRnnDecode(collection, HTRmodelid, dictionaryName, mydocid, jstring, bDictTemp=False)
        seconds = 80 * len(pids)
        return wait_for_jobstatus(jobid, seconds, mytkbs, count=5)
    except Exception as e:
                print("ERROR in run_ocr for docid " + str(mydocid))
                print (e)
                print ("END ERROR \n\n")
                pass




def download(collection, documentid, folder, mytkbs, metafilename):
    try:
        response = mytkbs.download_document(collection, documentid, folder)
        #print(response)
        pages = len(response[1])
        if pages > 0:
            #print(str(pages) + " pages of doc download completed.")
            with open(os.path.join(folder, metafilename)) as j:  
                data = json.load(j)
                #print(data)
                return data
        else:
            #print("no pages downloaded.")
            return None
    except Exception as e:
                print("ERROR in download ")
                print (e)
                print ("END ERROR \n\n")
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

#check if dir exists, creates it if not
def prep_dir(out_dir):
    try:
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        return(out_dir)
    except Exception as e: 
        print("ERROR in prep_dir " + out_dir)
        print (e)
        print ("END ERROR \n\n")
        raise e

def wait_for_jobstatus(job, waitseconds, mytkbs, count=1):
    try:
        #print("waiting " + str(waitseconds) + ", checking jobid " + str(job))
        c = 0
        while c < count:
            c += 1
            if waitseconds > 0:
                time.sleep(waitseconds)
            response = mytkbs.getJobStatus(str(job))
            if response['state'] == 'FINISHED':
                return response['success']
            else:
                if c == count:
                    return False
    except Exception as e:
                print("ERROR in wait_for_jobstatus ")
                print (e)
                print ("END ERROR \n\n")
                pass

def line_detect(collection, mydocid, pageids, mytkbs):
    try:
        doc_parts = '{"docList" : {"docs" : [ {"docId" : ' + str(mydocid) + ', "pageList" : {"pages" : ['
        psik = ', '
        count = 0
        total = len(pageids)
        for number, pageid in pageids.items():
            count += 1
            if count == total:
                psik = ''
            doc_parts = doc_parts + '{"pageId" : ' + str(pageid) + '}' + psik
        doc_parts = doc_parts + ']}}]}}'
        response = mytkbs.analyzeLayout(colId=collection, docPagesJson=doc_parts, bBlockSeg=False, bLineSeg=True)
        tree = ElementTree.fromstring(response)
        status = tree.find('trpJobStatus')
        jobId = status.find('jobId').text
        seconds = total * 60
        return wait_for_jobstatus(jobId, seconds, mytkbs, count=5)
    except Exception as e:
                print("ERROR in line_detect ")
                print (e)
                print ("END ERROR \n\n")
                pass

def edit_pg_baseline(pgfile, addpoints):
    ET.register_namespace('', "http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15")
    tree = ET.ElementTree(file=pgfile)
    xml_changed = False
    for myelement in tree.iterfind('*/*/*/*'):
        if myelement.tag.endswith("Baseline"):
            xml_changed = True
            points = myelement.attrib.get('points')
            points_list = points.split(" ")
            startpoint = str(int(points_list[0].split(",")[0]) - addpoints) + "," + points_list[0].split(",")[1]
            endpoint = str(int(points_list[(len(points_list) - 1)].split(",")[0]) + addpoints) + "," + points_list[(len(points_list) - 1)].split(",")[1]
            new_points = startpoint + " " + points + " " + endpoint
            myelement.set('points', new_points)
    if (xml_changed):
        tree.write(pgfile)
        #print("BASELINE CHANGED: " + pgfile)
        return True
    else:
        return False

v = False
def upload_pipeline(config):
    folders_to_be_uploaded = find_sub_folders_with_toc_file(config.src_path)
    workfolder = os.path.join(config.src_path, "tkbs_work")
    prep_dir(workfolder)
    outfolder = os.path.join(config.src_path, "tkbs_output")
    prep_dir(outfolder)
    legacy_output = os.path.join(config.src_path, "legacy_output")
    collec = config.collection_id
    user = config.username
    key = config.password
    HTRmodelid = config.htr_model_id
    disable_warnings(InsecureRequestWarning)
    tkbs = TranskribusClient(sServerUrl = "https://transkribus.eu/TrpServer")
    tkbs.auth_login(user, key, True)

    for sfolder in folders_to_be_uploaded:
        try:
            if not os.path.isfile(os.path.join(sfolder, 'TOC.xml')):
                continue
            infolder = sfolder
            
            start = str(datetime.datetime.now().strftime("%y-%m-%d-%H-%M"))
            print(start + " - " + infolder)# + "\n==============")
            v and print("---   CREATING DATA to upload  ---")
            p = Document()
            p.load_legacy_data(infolder)
            uniquename = p.doc_title + "_" + start
            exportfolder = os.path.join(outfolder, "tkbs_" + uniquename)
            prep_dir(exportfolder)
            
            firstexportdir = sfolder.replace(config.src_path, legacy_output)
            if not os.path.isdir(firstexportdir):
                print("Skipping... TKBS output missing under " + firstexportdir)
                continue
            v and print("---   UPLOADING data to server       ---")
            v and print("from " + firstexportdir)
            docid = upload(collec, firstexportdir, p.img_names_by_pgnum(), p.pxml_names_by_pgnum(), p.title, user, "pipeline test", tkbs)
            if docid <= 0:
                print ("ERROR - document failed to upload " + p.title)
                continue 
            
            v and print("---   DOWNLOADING-1 doc for page ids       ---")
            tempdowndir = prep_dir(os.path.join(workfolder, "tempdowndir"))
            target_dir = os.path.join(tempdowndir, uniquename + "_" + str(collec) + "_" + str(docid))
            docjson = download(collec, str(docid), target_dir, tkbs, p.tkbs_meta_filename)
            pageids = p.load_tkbs_page_ids(docjson)
            
            v and print("---   LINE DETECTION          ---")
            detection_status = line_detect(collec, docid, pageids, tkbs)
            if not detection_status:
                print ("ERROR - document failed line detection " + p.title)
                continue 
            
            v and print("---   DOWNLOADING-2 doc for baseline extention      ---")
            extentiondowndir = os.path.join(workfolder, "extentiondowndir")
            prep_dir(extentiondowndir)
            xtarget_dir = os.path.join(extentiondowndir, uniquename + "_" + str(collec) + "_" + str(docid))
            xdocjson = download(collec, str(docid), xtarget_dir, tkbs, p.tkbs_meta_filename)
            xpageids = p.load_tkbs_page_ids(xdocjson)
            
            v and print("---   BASELINE EXTENTION         ---")
            for num, fname in p.pxml_names_by_pgnum().items():
                fullname = os.path.join(xtarget_dir, fname)
                edit_pg_baseline(fullname, 10)
            
            v and print("---   UPLOAD extended baseline data to server          ---")
            xdocid = upload(collec, xtarget_dir, p.img_names_by_pgnum(), p.pxml_names_by_pgnum(), p.title, user, "pipeline test baseline extended", tkbs)
            if xdocid <= 0:
                print ("ERROR - document failed to upload after baseline extention" + p.title)
                continue #sys.exit(1)
            
            v and print("---   DOWNLOADING-3 doc for ocr page ids      ---")
            preocr = os.path.join(workfolder, "preocr")
            prep_dir(preocr)
            preocr_dir = os.path.join(preocr, uniquename + "_" + str(collec) + "_" + str(xdocid))
            pdocjson = download(collec, str(xdocid), preocr_dir, tkbs, p.tkbs_meta_filename)
            ppageids = p.load_tkbs_page_ids(pdocjson)
            
            
            v and print("---   RUNNING OCR          ---")
            ocr_status = run_ocr(collec, HTRmodelid, "", str(xdocid), ppageids, tkbs)
            if not ocr_status:
                print ("ERROR - document failed ocr " + p.title)
                continue #sys.exit(1)
            
            v and print("---   FINAL DOWNLOAD after OCR for TEI export        ---")
            ocrdowndir = os.path.join(exportfolder, "transkribus")
            prep_dir(ocrdowndir)
            otarget_dir = os.path.join(ocrdowndir, uniquename + "_" + str(collec) + "_" + str(xdocid))
            ocrdocjson = download(collec, str(xdocid), otarget_dir, tkbs, p.tkbs_meta_filename)
            pageids = p.load_tkbs_page_ids(ocrdocjson)
            
    
            
        except Exception as e:
            print("ERROR in PipelineRunner main loop ")
            print (e)
            print ("END ERROR \n\n")
            pass


    print("DONE. Output is under " + outfolder)
    tkbs.auth_logout()


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

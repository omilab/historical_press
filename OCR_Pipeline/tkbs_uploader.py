import json
import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
import xml.etree.cElementTree as ET
import datetime
from xml.etree import ElementTree
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning
from TkbsApiClient import TranskribusClient
from TkbsDocument import Document

class Config:
    def __init__(self, config_parameters=None):
        self.default_garbage_line_width = 13
        if os.path.isfile('conf.json'):
            with open('conf.json') as json_file:
                conf_json = json.load(json_file)
            self.username = conf_json["username"]
            self.password = conf_json["password"]
            self.src_path = conf_json["src_path"]
            self.collection_id = conf_json["collection_id"]
            self.line_detection = conf_json["line_detection"]            
            self.htr_model_id = conf_json["htr_model_id"]
            self.htr_lang_model = conf_json["htr_language_model"]
            self.user_garbage_line_width = conf_json["garbage_line_width"]
            
        elif config_parameters is None:
            self.username = set_username()
            self.password = set_password()
            self.src_path = set_source_path()
            self.collection_id = set_collection_id()
            self.line_detection = set_line_detection_id()
            self.htr_model_id = set_htr_model_id()
            self.htr_lang_model = set_htr_language_model()
            self.user_garbage_line_width = get_garbage_lines_width(self.default_garbage_line_width)
        else:
            self.username, self.password, self.src_path, self.collection_id, \
            self.line_detection, self.htr_model_id, self.htr_lang_model, \
            self.user_garbage_line_width = config_parameters

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
    line_detection_id = input("Press Enter for default line detection, or something else to only upload, skipping line detection and the following stages: ")
    return "Skip" if line_detection_id.strip() != "" else ""


def set_htr_model_id():
    htr_model_id = input("Enter your HTR model id (or press Enter if you don't want text recognition): ")
    return str(htr_model_id)


def get_garbage_lines_width(width):
    user_input = input("Garbage line default width is " + str(width) +\
                       " points.\npress Enter for default width, or type a different width, zero to disable garbage cleanup: ")
    try:
        newwidth = int(user_input)
        if newwidth <= 0:
            print("Garbage line cleanup disabled\n")
        else:
            print("Garbage line width will be set to " + str(newwidth) + " points.\n")
        return newwidth
    except:
        print("Using default value\n")
        return width

def set_htr_language_model():
    user_input = input("Enter 'YES' to activate the HTR integrated language model: ")
    try:
        if user_input.upper() == 'YES':
            return True
        else: 
            return False
    except:
        return False
        

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
            return int(docid)
        else:
            print("ERROR - " + str(count) + " files of " + total + " completed.")
            return -1
    except Exception as e:
                print("ERROR in upload ")
                print (e)
                print ("END ERROR \n\n")
                pass


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
        return wait_for_jobstatus(jobid, seconds, mytkbs, count=10)
    except Exception as e:
                print("ERROR in run_ocr for docid " + str(mydocid))
                print (e)
                print ("END ERROR \n\n")
                pass

def run_ocr_with_options(collection, HTRmodelid, dictionaryName, mydocid, pids, mytkbs):
    try:
        total = len(pids)
        jstring = '{"docId" : ' + str(mydocid) + ', "pageList" : {"pages" : ['
        psik = ', '
        count = 0
        for pnum, pid in pids.items():
            count += 1
            if count == total:
                psik = ''
            jstring = jstring + '{"pageId" : ' + str(pid) + '}' + psik
        jstring = jstring + ']}}'
        jobid = mytkbs.htrRnnDecode(collection, HTRmodelid, dictionaryName, mydocid, jstring, bDictTemp=False)
        seconds = 80 * len(pids)
        return wait_for_jobstatus(jobid, seconds, mytkbs, count=10)
    except Exception as e:
                print("ERROR in run_ocr for docid " + str(mydocid))
                print (e)
                print ("END ERROR \n\n")
                pass

def get_doc(collection, mydocid, mytkbs):
    try:
        return mytkbs.getDocById(collection, mydocid)
    except Exception as e:
                print("ERROR in get_doc for docid " + str(mydocid))
                print (e)
                print ("END ERROR \n\n")
                pass
    

def download(collection, documentid, folder, mytkbs, metafilename):
    try:
        response = mytkbs.download_document(collection, documentid, folder)
        pages = len(response[1])
        if pages > 0:
            with open(os.path.join(folder, metafilename)) as j:  
                data = json.load(j)
                return data
        else:
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
        seconds = total * 5
        return wait_for_jobstatus(jobId, seconds, mytkbs, count=12)
    except Exception as e:
                print("ERROR in line_detect ")
                print (e)
                print ("END ERROR \n\n")
                pass

   
def delete_garbage_text(pgfile, garbage_line_width):
    ET.register_namespace('', "http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15")
    tree = ET.ElementTree(file=pgfile)
    xml_changed = False
    for myelement in tree.iterfind('*/*/*'):
        if myelement.tag.endswith("TextLine"):
            line_changed = False
            textchild = None
            for mychild in myelement.getiterator():
                if mychild.tag.endswith("TextEquiv"):
                    textchild = mychild
                if mychild.tag.endswith("Baseline"):
                    points = mychild.attrib.get('points')
                    points_list = points.split(" ")
                    smallpoint = int(points_list[0].split(",")[0])
                    bigpoint = int(points_list[(len(points_list) - 1)].split(",")[0])
                    linewidth = bigpoint - smallpoint
                    if linewidth <= garbage_line_width:
                        xml_changed = True
                        line_changed = True
            if line_changed and textchild != None:
                for tnode in textchild.getiterator():
                    tnode.text = ""
    if (xml_changed):
        tree.write(pgfile)
        return True
    else:
        return False

v = False
def upload_pipeline(config):
    folders_to_be_uploaded = find_sub_folders_with_toc_file(config.src_path)
    outfolder = os.path.join(config.src_path, "transkribus_output")
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
            print(start + " - " + infolder)
            v and print("---   CREATING DATA to upload  ---")
            p = Document()
            p.load_legacy_data(infolder)
            uniquename = p.doc_title + "_" + start
            firstexportdir = sfolder.replace(config.src_path, legacy_output)
            if not os.path.isdir(firstexportdir):
                print("Skipping... TKBS output missing under " + firstexportdir + "\nRun stage-1 script  first, to convert legacy to transkribus format.")
                continue
            v and print("---   UPLOADING data to server       ---")
            v and print("from " + firstexportdir)
            docid = upload(collec, firstexportdir, p.img_names_by_pgnum(), p.pxml_names_by_pgnum(), p.title, user, "pipeline test", tkbs)
            if docid <= 0:
                print ("ERROR - document failed to upload " + p.title)
                continue 
            
            v and print("---   GETTING page ids       ---")
            docjson = get_doc(collec, docid, tkbs)
            pageids = p.load_tkbs_page_ids(docjson)
            
            if config.line_detection != None and config.line_detection.upper() == "SKIP":
                v and print("Skipping from Line Detection and on...")
                continue
            
            v and print("---   LINE DETECTION          ---")
            detection_status = line_detect(collec, docid, pageids, tkbs)
            if not detection_status:
                print ("ERROR - document failed line detection " + p.title)
                continue 
            
            
            if len(HTRmodelid) < 2:
                v and print("Skipping from Htr and on...")
                continue
                
            v and print("---   RUNNING OCR          ---")
#            ocr_status = run_ocr_with_options(collec, HTRmodelid, "", str(446788), {}, tkbs)
            dictionary = ""
            if config.htr_lang_model != None and config.htr_lang_model:
                dictionary = "trainDataLanguageModel"
                v and print("Using trainDataLanguageModel")
            ocr_status = run_ocr(collec, HTRmodelid, dictionary, str(docid), pageids, tkbs)
            if not ocr_status:
                print ("ERROR - document failed ocr " + p.title + " with status " + str(ocr_status))
                continue 
            
            v and print("---   FINAL DOWNLOAD after OCR for TEI export        ---")
            otarget_dir = os.path.join(outfolder, uniquename + "_" + str(collec) + "_" + str(docid))
            ocrdocjson = download(collec, str(docid), otarget_dir, tkbs, p.tkbs_meta_filename)
            pageids = p.load_tkbs_page_ids(ocrdocjson)
            
            width = config.default_garbage_line_width
            try:
                width = int(config.user_garbage_line_width)
            except:
                width = config.default_garbage_line_width
            if width > 0:
                v and print("---   DELETING GARBAGE TEXT         ---")
                for num, fname in p.pxml_names_by_pgnum().items():
                    fullname = os.path.join(otarget_dir, fname)
                    delete_garbage_text(fullname, width)

            
        except Exception as e:
            print("ERROR in upload_pipeline main loop ")
            print (e)
            print ("END ERROR \n\n")
            pass


    print("DONE. Output is under " + outfolder)
    tkbs.auth_logout()


def upload_a_folder(sfolder):
    user = config.username
    outfolder = os.path.join(config.src_path, tkbs_subfolder)
    prep_dir(outfolder)
    legacy_output = os.path.join(config.src_path, "legacy_output")
    collec = config.collection_id
    HTRmodelid = config.htr_model_id
    infolder = sfolder
    OkayMessage = "Done OKAY " + infolder
    ErrorMessage = "Done with ERRORs " + infolder

    try:
        if not os.path.isfile(os.path.join(sfolder, 'TOC.xml')):
            return(ErrorMessage)

        start = str(datetime.datetime.now().strftime("%y-%m-%d-%H-%M"))
        print(start + " - " + infolder)
        v and print("---   CREATING DATA to upload  ---")
        p = Document()
        p.load_legacy_data(infolder)
        uniquename = p.doc_title + "_" + start
        firstexportdir = sfolder.replace(config.src_path, legacy_output)
        if not os.path.isdir(firstexportdir):
            print(p.doc_title + " Skipping... TKBS output missing under " + firstexportdir + "\nRun stage-1 script  first, to convert legacy to transkribus format.")
            return(OkayMessage)
        v and print(p.doc_title + "---   UPLOADING data to server       --- from " + firstexportdir)
        docid = upload(collec, firstexportdir, p.img_names_by_pgnum(), p.pxml_names_by_pgnum(), p.title, user, "pipeline test", tkbs)
        if docid <= 0:
            print (p.doc_title + "ERROR - document failed to upload " + p.title)
            return(ErrorMessage) 
        
        v and print(p.doc_title + "---   GETTING page ids       ---")
        docjson = get_doc(collec, docid, tkbs)
        pageids = p.load_tkbs_page_ids(docjson)
        
        if config.line_detection != None and config.line_detection.upper() == "SKIP":
            v and print(p.doc_title + "Skipping from Line Detection and on...")
            return(OkayMessage)
        
        v and print(p.doc_title + "---   LINE DETECTION          ---")
        detection_status = line_detect(collec, docid, pageids, tkbs)
        if not detection_status:
            print (p.doc_title + "ERROR - document failed line detection " + p.title)
            return(ErrorMessage) 
        
        
        if len(HTRmodelid) < 2:
            v and print(p.doc_title + "Skipping from Htr and on...")
            return(OkayMessage)
            
        v and print(p.doc_title + "---   RUNNING OCR          ---")
    #            ocr_status = run_ocr_with_options(collec, HTRmodelid, "", str(446788), {}, tkbs)
        dictionary = ""
        if config.htr_lang_model != None and config.htr_lang_model:
            dictionary = "trainDataLanguageModel"
            v and print(p.doc_title + "Using trainDataLanguageModel")
        ocr_status = run_ocr(collec, HTRmodelid, dictionary, str(docid), pageids, tkbs)
        if not ocr_status:
            print (p.doc_title + "ERROR - document failed ocr " + p.title + " with status " + str(ocr_status))
            return(ErrorMessage)  
        
        v and print(p.doc_title + "---   FINAL DOWNLOAD after OCR for TEI export        ---")
        otarget_dir = os.path.join(outfolder, uniquename + "_" + str(collec) + "_" + str(docid))
        ocrdocjson = download(collec, str(docid), otarget_dir, tkbs, p.tkbs_meta_filename)
        pageids = p.load_tkbs_page_ids(ocrdocjson)
        
        width = config.default_garbage_line_width
        try:
            width = int(config.user_garbage_line_width)
        except:
            width = config.default_garbage_line_width
        if width > 0:
            v and print(p.doc_title + "---   DELETING GARBAGE TEXT         ---")
            for num, fname in p.pxml_names_by_pgnum().items():
                fullname = os.path.join(otarget_dir, fname)
                delete_garbage_text(fullname, width)
                
        return(OkayMessage)
    except Exception as e:
        print(p.doc_title + "ERROR in upload_a_folder ")
        print (e)
        print (p.doc_title + "END ERROR \n\n")
        return(ErrorMessage)
    
    
def upload_parallel():
    disable_warnings(InsecureRequestWarning)
    user = config.username
    key = config.password
    tkbs.auth_login(user, key, True)
    folders_to_be_uploaded = find_sub_folders_with_toc_file(config.src_path)    
    with ThreadPoolExecutor(max_workers = 3) as executor:
        results = executor.map(upload_a_folder, folders_to_be_uploaded)
    for result in results:
        print(result)
    

    print("PARALLEL UPLOAD DONE. Output is under " + os.path.join(config.src_path, tkbs_subfolder))
    tkbs.auth_logout()


config = Config(["<user email>", "<user password>", r'<legacy top folder>', \
                 "<transkribus collection id>", None, "<transkribus htr model>", True, ""])
tkbs_subfolder = "transkribus_output"
tkbs = TranskribusClient(sServerUrl = "https://transkribus.eu/TrpServer")
def main():
    upload_parallel()


if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
"""
OMILAB 2019 - Run a sequence of data conversions and Transkribus-API transactions to ocr and convert a Legacy NLI document to TEI.xml
"""

from TkbsDocument import Document
from TkbsApiClient import TranskribusClient
from xml.etree import ElementTree
import xml.etree.cElementTree as ET
import json, os, sys, time, datetime, glob

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


v = False

v and print("---   CONNECTING to server    ---")
user = "<user.name@email.com>" #CHANGE THIS
key = "<password>" #CHANGE THIS
collec = "17989" #CHANGE THIS
tkbs = TranskribusClient(sServerUrl = "https://transkribus.eu/TrpServer")
tkbs.auth_login(user, key, True)
#HTRmodelname = 'Test'
HTRmodelid = "10168" #CHANGE THIS
#dictName =  "Hebrew_Test.dict" #CHANGE THIS
#print("session id: " + tkbs.getSessionId() + "\n=================")


outfolder = r'<WORK FOLDER>\output' #CHANGE THIS
workfolder = prep_dir(os.path.join(outfolder, 'work'))
exportfolder = prep_dir(os.path.join(outfolder, 'export'))

subfolders = [x[0] for x in os.walk(r'<WORK FOLDER>\input')] #CHANGE THIS

for sfolder in subfolders:
    try:
        if not os.path.isfile(os.path.join(sfolder, 'TOC.xml')):
            continue
        infolder = sfolder 
        start = str(datetime.datetime.now().strftime("%y-%m-%d-%H-%M"))
        print(start + " - " + infolder)# + "\n==============")

        v and print("---   CREATING DATA to upload  ---")
        p = Document()
        #p.set_factors(150, 1.7238, 0.67)
        p.load_legacy_data(infolder)
        
        teifolder = os.path.join(exportfolder, 'tei')
        teifiles = glob.glob(teifolder + r'\*' + p.doc_title + r'*_tei.xml')
        if len(teifiles) > 0:
            v and print("TEI found, Skipping document " + p.doc_title)
            continue
        
        uniquename = p.doc_title + "_" + start
        firstuploadtopdir = prep_dir(os.path.join(workfolder, r'pagexml_for_upload'))
        firstexportdir = prep_dir(os.path.join(firstuploadtopdir, uniquename))
        p.export_tkbs_format(firstexportdir)
        
        
        
        v and print("---   UPLOADING data to server       ---")
        docid = upload(collec, firstexportdir, p.img_names_by_pgnum(), p.pxml_names_by_pgnum(), p.title, user, "pipeline test", tkbs)
        if docid <= 0:
            print ("ERROR - document failed to upload " + p.title)
            continue 
        
        v and print("---   DOWNLOADING-1 doc for page ids       ---")
        tempdowndir = prep_dir(os.path.join(workfolder, "tempdowndir"))
        target_dir = os.path.join(tempdowndir, p.title + "_" + str(collec) + "_" + str(docid))
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
        xtarget_dir = os.path.join(extentiondowndir, p.title + "_" + str(collec) + "_" + str(docid))
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
        preocr_dir = os.path.join(preocr, p.title + "_" + str(collec) + "_" + str(xdocid))
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
        otarget_dir = os.path.join(ocrdowndir, p.title + "_" + str(collec) + "_" + str(xdocid))
        ocrdocjson = download(collec, str(xdocid), otarget_dir, tkbs, p.tkbs_meta_filename)
        pageids = p.load_tkbs_page_ids(ocrdocjson)
        
        

        
        v and print("---   TEI export           ---")
        tkbsfolder = otarget_dir 
        p.load_tkbs_data(tkbsfolder)
        p.load_legacy_articles(p.legacy_metafile)
        p.match_legacy_articles()
        p.export_tei(teifolder)


        v and print("---   CSV export           ---")
        csvfolder = os.path.join(exportfolder, 'csv')
        p.export_csv(csvfolder)

        
        v and print("---   PLAINTEXT export     ---")
        
        plaintextfolder = os.path.join(exportfolder, 'plaintext')
        prep_dir(teifolder)
        p.export_plaintext(plaintextfolder)
        

        
    except Exception as e:
        print("ERROR in PipelineRunner main loop ")
        print (e)
        print ("END ERROR \n\n")
        pass



tkbs.auth_logout()

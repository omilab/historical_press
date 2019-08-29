#!/usr/bin/env python
# coding: utf-8
# To run totkbs, use python 2.7 and install dependencies with "pip install -r requirements.txt"

import os
from TkbsApiClient import TranskribusClient
import xml.etree.ElementTree as ET
from TkbsDocument import Document
import json
import sys
import pickle
import requests.exceptions
import time
from lxml import etree
import random
import getpass
import ast

def log(s_or_e, msg):
    label = ["STARTING: ", "DONE WITH: "]
    print label[s_or_e] + msg

# OCR Pipeline: From Legacy through PAGE.xml to XML-TEI
# The data flow includes the following suggested steps, which can be modified as needed:
# 1. Convert Olive software produced physical and logical (PRXML layout data into a PAGE xml (pxml) format. The conversion excludes the document text, which is assumed to contain errors.
# 2. Upload pxmls and scans of the document into Transkribus server.
# 3. Run Baseline detection for the document on Transkribus server.
# 4. Download the document.
# 5. Modify and extend baselines coordinates.
# 6. Upload the document.
# 7. Run HTR for the document on Transkribus server.
# 8. Download the document.
# 9. Convert and combine the document data into TEI format.

# in ar file get XMD-entity with id of ar and get box val
# in pg file get Entity with id of ar and get box val
# split return
def get_coords(filename, article, ispagefile):
    tree = etree.parse(filename)
    if not ispagefile:
        elem = tree.xpath('//XMD-entity')
        if elem[0].get("ID") != article:
            print "Getting coordinates: seems to be wrong article file"
        return elem[0].get("BOX").split()
    if ispagefile:
        for entity in tree.xpath('//Entity'):
            if entity.get("ID") == article:
                resolution = 0
                for res in tree.xpath('//Resolution'):
                    res_text = res.text
                    if int(res_text) > resolution:
                        resolution = int(res_text)
                return (resolution, entity.get("BOX").split())

def get_files(issue):
    pdir = "Document"
    path = os.path.join(issue, pdir)
    dirlist = os.listdir(path)
    pagepath = dirlist[random.randint(0,len(dirlist)-1)]
    while not os.path.isdir(os.path.join(path,pagepath)):
        pagepath = dirlist[random.randint(0,len(dirlist)-1)]
    path = os.path.join(path,pagepath)
    # choose a Ar and Pg file
    article_f = None
    page_f = None
    for f in os.listdir(path):
        if (f.lower().startswith("ar") or f.lower().startswith("ad")) and f[len(f)-4:] == ".xml" and article_f is None:
            article_f = f
        elif f.lower().startswith("pg") and f[len(f)-4:] == ".xml" and page_f is None:
            page_f = f
        if article_f and page_f:
            break
    if not article_f and not page_f:
        print "Required files in \"{}\" not found! Check if this directory belongs here. Trying again nonetheless.".format(path)
        return get_files(issue)
    article = article_f[:len(article_f)-4]
    return [article, os.path.join(path, article_f), os.path.join(path, page_f)]

def avg_coords(newcoords, oldcoords):
    sum = 0.0
    for n, o in zip(newcoords, oldcoords):
        if float(o) != 0:
            sum += (float(n)/float(o))
    sum = sum/4.0
    return sum

def calc_factor(issue):
    factor = 0.0
    def_factor2 = 4.0
    sample_cnt = 10
    if config['sample_cnt'] > 0:
        sample_cnt = config['sample_cnt']
    for x in range(0,sample_cnt):
        # choose a page directory
        files = get_files(issue)
        article = files[0]
        article_f = files[1]
        page_f = files[2]
        # get coordinates
        new_coord = get_coords(article_f, article, False)
        og_coord = get_coords(page_f, article, True)
        resolution = og_coord[0]
        og_coord = og_coord[1]
        # get average difference
        avg = avg_coords(new_coord, og_coord)
        factor += avg
    return [int(resolution), factor/float(sample_cnt), def_factor2]

# getting list of pxml filenames and their imagefile names
def pxml_list(main_dir):
    pxml_dic = {}
    for x in sorted(os.listdir(os.path.join(main_dir,config['pxml_dir']))):
        if int(x[2:5]) not in pxml_dic:
            pxml_dic[int(x[2:5])] = [x]
            pxml_dic[int(x[2:5])].append(open(os.path.join(main_dir,config['pxml_dir'],x),'rb'))
        else:
            pxml_dic[int(x[2:5])].append(x)
            pxml_dic[int(x[2:5])].append(open(os.path.join(main_dir,config['pxml_dir'],x),'rb'))

    pagelist = ""
    page_format = '{{"fileName": "{}", "pageXmlName": "{}", "pageNr": {}}},'
    for y, x in pxml_dic.items():
        pagelist += page_format.format(x[0],x[2],str(y))
    pagelist = "[{}]".format(pagelist[:len(pagelist)-1])
    return (pagelist, pxml_dic)

# Convert Abbyy Olive document layout into PageXML format
def make_pxml(res=None, f1=None, f2=None, factors=None):
    log(0,"pxml")
    p = Document()
    if type(config['factors']) == list:
        for f in config['factors']:
            p.set_factors(f[0], f[1], f[2])
    elif factors is not None:
        for f in factors:
            p.set_factors(f[0], f[1], f[2])
    if res is not None:
        p.set_factors(res,f1,f2)
    # directory containing TOC.xml
    p.load_legacy_data(paper)
    p.export_tkbs_format(os.path.join(paper, config['pxml_dir']))
    log(1,"pxml")

def tkbs_login():
    # use TrpServer not TrpServerTesting
    tkbs = TranskribusClient(sServerUrl='https://transkribus.eu/TrpServer')
    if tkbs.auth_login(config['user'], config['key'], True) is False:
        print "transkribus login error"
        #print("session id: " + tkbs.getSessionId())
    return tkbs

# Upload PageXML format into Transkribus server
# For Transkribus documentation: https://transkribus.eu/wiki/index.php Upload_via_REST_API
def upload_pxml():
    log(0,"upload")
    pxml_info = pxml_list(paper)

    jstring = '{{"md":     {{"title": "{t}", "author": "{a}", "description": "{d}"}}, "pageList":     {{"pages": {p}}}}}'.format(t=config['upload_title'], a=config['author'], d=config['upload_desc'], p=pxml_info[0])

    pfiles = []
    desc = 'application/octet-stream'
    for p_num, info in pxml_info[1].items():
        pfiles.append({'img': (info[0], info[1], desc), 'xml': (info[2], info[3], desc)})

    response = tkbs.createDocFromImages(config['collection'], jstring, pfiles)
    response_xml = ET.fromstring(response)
    uploadid = response_xml.find('uploadId').text
    log(1,"upload")
    return uploadid

def get_pagelist(upid):
    #get pagenumbers from the documents we just uploaded in "collection"
    #tkbs.reusePersistentSession()
    global tkbs
    tries = 1
    timeout = 5
    while True:
        try:
            cinfo = tkbs.getDocByIdAsXml(config['collection'],upid, nrOfTranscripts=0,bParse=False)
        except requests.exceptions.HTTPError as e:
            if int(e.response.status_code) == 404 and tries <= 5:
                print "Can't access the uploaded document: Transkribus hasn't yet refreshed their server. Trying again " + str(tries) + "/5."
                tkbs.cleanPersistentSession()
                tkbs.auth_logout()
                time.sleep(timeout*tries)
                tkbs = tkbs_login()
                tries += 1
                print e
                continue
            else:
                break
        print "Accessed!"
        break

    cinfoxml = ET.fromstring(cinfo)
    pages = set()
    for page in cinfoxml.iter('pageId'):
        pages.add(page.text)
    page_form =  '{{"pageId" : {} }}'
    page_list = ""
    for p in pages:
        page_list += page_form.format(p) + ","
    page_list = page_list[:len(page_list)-1]
    return page_list

# Run Baseline Detection
# For Transkribus documentation: https://transkribus.eu/wiki/index.php/Layout_Analysis_API
def base_line(upid, plist):
    log(0,"baseline")
    doc_parts = '{       "docList" : {          "docs" : [ {             "docId" : ' + upid + ',             "pageList" : {                "pages" : [ ' + plist + ' ]             }          } ]       }    }'
    d = json.loads(doc_parts)
    response = tkbs.analyzeLayout(colId=config['collection'], docPagesJson=doc_parts, bBlockSeg=False, bLineSeg=True)
    log(1,"baseline")
    return response

# Download Transkribus Document
def download_tkbsdoc(upid):
    log(0,"download")
    try:
        response = tkbs.download_document(config['collection'], upid, os.path.join(paper, config['tkribus_dir']))
    except Exception as e:
        if str(e).find("unless bForce=True") > -1:
            force_dwnld = raw_input("Overwrite? [yes/no] ")
            if force_dwnld.lower() == "yes":
                response = tkbs.download_document(config['collection'], upid, os.path.join(paper, config['tkribus_dir']), bForce=True)
    log(1,"download")
    #print(response)

# Extend Baseline Coordinates
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
        print("BASELINE CHANGED: " + pgfile)

def edit_baseline():
    log(0,"baseline")
    for root, dirs, files in os.walk(os.path.join(paper, config['tkribus_dir'])):
        for fname in files:
            if fname.upper().endswith(".PXML") and fname.upper().startswith("PG"):
                fullname = os.path.join(root,fname)
                edit_pg_baseline(fullname, 10)
    log(1,"baseline")

# Run OCR
# For Transkribus documentation: https://transkribus.eu/wiki/index.php/HTR#Recognition
def ocr():
    log(0,"ocr")
    dictionaryName = ""

    jstring = '{    "docId" : ' + uploadid + ',        "pageList" : {            "pages" : [ ' + page_list + ' ]        }    }'
    try:
        response = tkbs.htrRnnDecode(config['collection'], config['HTRmodelid'], dictionaryName, uploadid, jstring, bDictTemp=False)
    except requests.exceptions.HTTPError as e:
        if int(e.response.status_code) == 400:
            print("OCR failed. Make sure your HTR model is shared with this collection " + config['collection'] + ".")
    log(1,"ocr")
    #print tkbs.getJobStatus(response)

def save_config(f, c):
    with open(f, "wb") as out:
        pickle.dump(c, out)

def set_config():
    global factors
    global config_f_def
    config = {}
    error = "Sorry that didn't work. Try again\n"
    # JPRESS DATA
    #where the hjp files are [base/lang/newspaper/issue/toc.xml]
    while True:
        try:
            config['base'] = raw_input("Enter base directory of the source documents."                                       "\nCan be as far as 'base' in [base/lang/newspaper/issue/toc.xml]: ")
        except Exception:
            print error
            continue
        break
    #depth
    while True:
        try:
            config['depth'] = int(raw_input("Enter depth of the toc.xml from the base.\nIn the example above it is 4: "))
        except Exception:
            print error
            continue
        break
    #where pxml results are to be stored
    config["pxml_dir"] = ".pxml_converted"
    #where the trankribus results are to be stored
    config["tkribus_dir"] = ".transkribus"

    #TRANSKRIBUS INFO
    #transkribus credentials
    while True:
        try:
            config['user'] = raw_input("Enter Transkribus username: ")
            config['key'] = getpass.getpass("Enter Transkribus password: ")
        except Exception:
            print error
            continue
        break
    #transkribus collection id for our destination collection (make new collection here?)
    while True:
        try:
            config['collection'] = raw_input("Enter Transkribus collection id, where the documents are to be added: ")
        except Exception:
            print error
            continue
        break
    # transkribus upload info
    while True:
        try:
            config['author'] = raw_input("Enter Transkribus author name: ")
            config['upload_title'] = raw_input("Enter the title of this upload: ")
            config['upload_desc'] = raw_input("Enter description of this upload: ")
            #choose the model you want--10163 is hameorerot
            config['HTRmodelid'] = raw_input("Enter the HTRmodelid to be used: ")
        except Exception:
            print error
            continue
        break
    #run full pipeline or upload only
    while True:
        try:
            upload_only = raw_input("Upload only instead of all pipeline processes? yes or no: ")
            if upload_only.lower() == "yes":
                config['upload_only'] = True
            else:
                config['upload_only'] = False
        except Exception:
            print error
            continue
        break
    # custom factors
    while True:
        try:
            custom_factors = raw_input("Enter a list of custom factors in the following format [[resolution, factor1, factor2], ...]\nOr enter '1' to have them calculated for each document, or '0' to use defaults: ")
            config['factors'] = custom_factors.strip()
            if config['factors'] == "1":
                config['factors'] = True
                while True:
                    try:
                        config['sample_cnt'] = int(raw_input("Enter number of textblocks from which to compute the factors: "))
                    except Exception:
                        print error
                        continue
                    break
            elif config['factors'] == "0":
                config['factors'] = False
            else:
                config['factors'] == ast.literal_eval(config['factors'])
        except Exception:
            print error
            continue
        break
    while True:
        try:
            c = raw_input("Enter a filename to save these configurations, 'def' for default filename, or 'no' not to save them: ")
            if c.lower() == "no":
                config_f = False
            elif c.lower() != "def":
                config_f = c
            else:
                config_f = config_f_def
        except Exception:
            print error
            continue
        break
    if config_f is not False:
        save_config(config_f, config)

    return config


config_f_def = "pipeline_config.pickle"
config = {}
# 144 factors = [[2.4883843518,.4]]
# 120 factors = [[2.4,.413]]
# 210 factors = [[2.46938191718,.413]]
# 180 factors = [[3.59747421296,.2889]]
# la epoca 180 factors = [[1.66539490841,.6]]
# magid 144 factors = [[2.00803520956,.5]]
# kbarat 150 factors = [[2.48414234145,.4]]
factors = [[144,2.4883843518,.4],
               [120,2.4,.413],
               [210,2.46938191718,.413],
               [180,3.59747421296,.2889],
               [150,2.48414234145,.4]]
help = "python " + sys.argv[0] + " [flags] [config_filename] [overideable_configs]\n\nflags:\n\t-p\tprint configurations to text file\n\t-s\tsave configurations if updated\n\t-h\thelp\n\noveridable_configs:\n\tbase=[base_directory]\n\tdepth=[1-4]\n\tcollection=[collection_id]\n\tHTRmodelid=[model_id]\n\tupload_only=[boolean]"
save_changes = False
print_config = False
config_f = None
# no args
if len(sys.argv) == 1:
    exists = os.path.isfile(config_f_def)
    if exists:
        print "No config file specified. Using default."
        try:
            with open(config_f_def, "rb") as f:
                config = pickle.load(f)
        except Exception:
            print "Pickled config file was too sour. Let's set them again."
            config = set_config()
    else:
        print "No config file specified and none found. Let's set them."
        config = set_config()
# yes args
elif len(sys.argv) > 1:
    for arg in sys.argv[1:]:
        # flags
        if arg[0] == "-":
            if arg.find("h") > -1:
                print help
                sys.exit(0)
            if arg.find("s") > -1:
                save_changes = True
            if arg.find("p") > -1:
                print_config = True
        # no config file (use defualt), but yes overide settings
        elif arg.find("=") > -1:
            if not any(config):
                try:
                    print "No config file specified. Using default."
                    with open(config_f_def, "rb") as f:
                        config = pickle.load(f)
                except Exception:
                    print "No config file specified and default not found. Let's set them again."
                    config = set_config()
            kv = arg.split("=")
            if kv[0] == "depth":
                config[kv[0]] = int(kv[1])
            elif kv[0] == "upload_only":
                config[kv[0]] = kv[1] == "True"
            else:
                config[kv[0]] = kv[1]
        # try specified config file
        else:
            try:
                # try unpickleing
                with open(arg, "rb") as f:
                    config = pickle.load(f)
                config_f = arg
            except Exception:
                print "The config file specified could not be used. Trying default."
                try:
                    #try unpickleing default
                    with open(config_f_def, "rb") as f:
                        config = pickle.load(f)
                except Exception as e:
                    print "The default config file was also bad. Let's set them again."
                    print e
                    config = set_config()
if type(config) != dict or not any(config):
    try:
        #try unpickleing default
        with open(config_f_def, "rb") as f:
            config = pickle.load(f)
    except Exception:
        print "Config file corrupted. Let's set them again"
        config = set_config()

if save_changes:
    if config_f is not None:
        save_config(config_f, config)
    else:
        save_config(config_f_def, config)
if print_config:
    config_text = ""
    for k, v in config.items():
        config_text = config_text + k + ": " + str(v) + "\n"
    if config_f is not None:
        with open(config_f + ".txt", "w") as ctf:
            ctf.write(config_text)
    else:
        with open(config_f_def + ".txt", "w") as ctf:
            ctf.write(config_text)
tkbs = tkbs_login()
paper = ""
if config['depth'] == 4:
    data_dirs = [(os.path.join(config['base'], x, y, w)) for x in os.listdir(config['base']) if not x.startswith(".") for y in os.listdir(os.path.join(config['base'], x)) if not y.startswith(".") for w in os.listdir(os.path.join(config['base'],x,y)) if not w.startswith(".")]
    [(count, data_dirs[count]) for count in range(len(data_dirs))]
elif config['depth'] == 3:
    data_dirs = [(os.path.join(config['base'], x, y)) for x in os.listdir(config['base']) if not x.startswith(".") for y in os.listdir(os.path.join(config['base'], x)) if not y.startswith(".")]
    [(count, data_dirs[count]) for count in range(len(data_dirs))]
elif config['depth'] == 2:
    data_dirs = [(os.path.join(config['base'], x)) for x in os.listdir(config['base']) if not x.startswith(".")]
    [(count, data_dirs[count]) for count in range(len(data_dirs))]
elif config['depth'] == 1:
    data_dirs = [config['base']]

for issue in data_dirs:
    log(0,issue)
    paper = issue
    # magid 144 factors = [[2.00803520956,.5]]
    # la epoca 180 factors = [[1.66539490841,.6]]
    # todo: custom rules per paper
    if type(config['factors']) == list:
        make_pxml()
    elif config['factors'] == True:
        fkts = calc_factor(issue)
        make_pxml(res=fkts[0], f1=fkts[1], f2=fkts[2])
    else:
        if issue.lower().find("magid") > -1:
            make_pxml(res=144,f1=2.00803520956,f2=.5, factors=factors)
        elif issue.lower().find("epoca") > -1:
            make_pxml(res=180,f1=1.66539490841,f2=.6, factors=factors)
        else:
            make_pxml(factors=factors)
    uploadid = upload_pxml()
    if config['upload_only'] is False:
        page_list = get_pagelist(uploadid)
        baseline_jobid = base_line(uploadid, page_list)
        while tkbs.getJobStatus(tkbs.getJobIDsFromXMLStatuses(baseline_jobid)[0])['state'] == "RUNNING":
            print "Waiting for baisline analysis to complete..."
            time.sleep(2)
        print "Baseline analysis completed!"
        download_tkbsdoc(uploadid)
        edit_baseline()
        ocr()
    log(1,issue)

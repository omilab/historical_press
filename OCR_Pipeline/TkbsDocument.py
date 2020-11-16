# -*- coding: utf-8 -*-
"""

OMILAB 2019
Convert Olive Legacy historical press Document format to Transkribus page-xml format, excluding word boxing and text.

"""

from lxml import etree
from shutil import copyfile
import os, sys, json, csv, mmap
import xml.etree.ElementTree as ET
import zipfile


class Document:

    def __init__(self):
        self.doc_id = None #from TOC.xml
        self.doc_title = None # from TOC.xml
        self.release_no = None #from TOC.xml
        self.legacy_metafile = "TOC.xml"
        self.docdir = "Document"
        self.legacydir = None
        self.tkbs_exportdir = None
        self.page_count = 0
        self.PagesImgResolutions = {} #key: page num, value: image resolution, from Pgxxx.xml
        self.PagesImgName = {} #key: page num, value: image filename, from TOC.xml
        self.PagesResolutionFactor = {} #key: page num, value: 1 or max_res / page_res
        self.PagesXmlName = {} #key: page num, value: Pg00x.xml filename, from TOC.xml
        self.EntitiesIndex = {} #key: Entity name, from TOC.xml, value:   entity TOC_ENTRY_ID
        self.EntitiesPage = {} #key: Entity name, value: entity PAGE_NO , from TOC.xml
        self.article_types = {} #key: Article Id, value: AR or AD, from TOC.xml
        self.input_pub_file_name = ""
        self.xmlcode = "UTF-8"
        self.cut_low_line_part = 0.33 #remove the lower part of the line box to help TKBS identify the baseline
        self.headline_primitive_type = 'HedLine_hl1'
        self.frame_primitive_type = 'AdFrame'
        self.graphic_primitive_type = 'Picture'
        self.inputdir_images = 'Img'
        self.outputdir_xmls = 'page'
        self.legacy_garbage_width = 13
        self.max_doc_resolution = None
        self.factor1 = None
        self.factor2 = None
        self.page_count = 0
        self.entity_counter = 0
        self.pxmlOutname = {}
        self.PagesImgHeight = {} #key: page num, value: image height, from Pgxxx.xml
        self.PagesImgWidth = {} #key: page num, value: image width, from Pgxxx.xml
        self.ContentPrimitives = [] # list of content primitives , from Pgxxx.xml
        self.PrimitivesIndexInPage = {} #key: prim calculated index from SEQ_NUM, value: Primitive Name, from Arxxx.xml
        self.RegionBoxing = {} #key: primitive id-name, value: primitive box converted to transkribus format, from Arxxx.xml
        self.LineBoxing = {} #key: lineId primitive_count, value: line box converted to transkribus format, from Arxxx.xml
        self.LineIndexInRegion = {} #key: lineId primitive_count, value: count
        self.PrimitiveTypes = {} #key: primitive id-name, value: primitive type from ELEMENT_TYPE Pgxxx.xml
        self.tkbs_meta_filename = "trp.json"
        self.tkbs_xml_schema = "http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15"
        self.tkbs_xsd = "http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15/pagecontent.xsd"
        self.tkbs_xsi = "http://www.w3.org/2001/XMLSchema-instance"
        self.tkbs_load_dir = None
        self.title = None
        self.colId = None
        self.colName = None
        self.docId = None
        self.toolName = None
        self.pages = {}
        self.articles = {}
        self.legacy_articles = {}
        self.HeaderPrimitives = [] #key: entity id, value: bool true if entity has HeadLine_hl1 primitive

    #remove garbage lines by identifying lines with very small width
    def is_garbage_line(self, linebox):
        try:
            xleft, ybottom, xright, ytop = linebox.split()
            line_width = int(xright) - int(xleft)
            if line_width <= self.legacy_garbage_width:
                return True
            else:
                return False
        except Exception as e:
            print("ERROR in is_garbage_line " + str(linebox))
            print (e)
            print ("END ERROR \n\n")
            return False
            pass
    
    def set_garbage_line_width(self, new_line_width):
        try:
            self.legacy_garbage_width = int(new_line_width)
        except:
            return
        
    #read Arxxx.xml file
    def get_legacy_entity_data(self, input_file_name):
        try:
            tree = etree.parse(input_file_name)
            #this works only for content primitives, rest of them are in Pgxxx.xml
            for content_child in tree.xpath('//Primitive'):
                content_id = content_child.get("ID")
                id_count = 1
                count = 1
                for line_child in content_child.xpath("L"):
                    line_id = content_id + "_" + str(id_count)
                    id_count = id_count + 1 #keeping full id count even if skipped, for backward compatibility
                    line_seq = count
                    legacy_box = line_child.get("BOX")
                    if not self.is_garbage_line(legacy_box):
                        line_box = self.calc_coordinates(self.modify_legacy_line_box(legacy_box, self.cut_low_line_part), self.factor1, self.factor2)
                        self.LineIndexInRegion[line_id] = line_seq
                        self.LineBoxing[line_id] = line_box
                        count = count + 1
        except Exception as e:
            print("ERROR in get_legacy_entity_data " + input_file_name)
            print (e)
            print ("END ERROR \n\n")
            pass
    
    def check_unzip(self, input_folder):
        input_zip = input_folder + ".zip"
        if not os.path.isdir(input_folder) and os.path.isfile(input_zip):
            os.makedirs(input_folder)
            os.chdir(os.path.dirname(input_zip))
            fh = open(input_zip, 'rb')
            z = zipfile.ZipFile(fh)
            for name in z.namelist():
                z.extract(name, input_folder)
            fh.close()

    def get_toc_article_types(self, tocfile):
        ettree = ET.parse(tocfile)
        xroot = ettree.getroot()
        for a in xroot.findall("Logic_np/TOC_Entries/TOC_Entry"):
            aid = a.attrib["TOC_ENTRY_ID"]
            atype = a.attrib["PRIM_ID_REF"][0:2]
            self.article_types[aid] = atype
    
    def load_legacy_data(self, inputdir):
        try:
            #---- READING TOC FILE ---------------------#
            self.legacydir = inputdir
            self.input_pub_file_name = os.path.join(self.legacydir, self.legacy_metafile)
            self.pick_max_resolution(self.input_pub_file_name)
            tree = etree.parse(self.input_pub_file_name)
            MetaElement = tree.xpath('//Xmd_toc')
            self.release_no = MetaElement[0].get("RELEASE_NO")
            self.title = MetaElement[0].get("RELEASE_NO")
            release_parts = self.release_no.split("-")
            self.doc_id = release_parts[2] + release_parts[3] + release_parts[4]
            self.doc_title = release_parts[1] + "-"+ release_parts[2] +"-"+ release_parts[3] +"-"+ release_parts[4]
            self.page_count = len(tree.xpath('//Page'))
            self.check_unzip(os.path.join(inputdir, self.docdir))
            for pgElement in tree.xpath('//Page'):
                pgNum = pgElement.get("PAGE_NO")
                pgXml = pgElement.get("ID") + ".xml"
                self.PagesXmlName[pgNum] = os.path.join(inputdir, self.docdir, pgNum, pgXml)
                
            #---- READING IMG RESOLUTIONS ---------------------#         
            count = 1
            while (count <= self.page_count):
                self.parse_legacy_page_img_resolution(str(count))
                count +=1
                
            for pgElement in tree.xpath('//Page'):
                pgNum = pgElement.get("PAGE_NO")
                pgId = pgElement.get("ID")
                self.pxmlOutname[pgNum] = pgId + "_" + self.PagesImgResolutions[str(pgNum)] + ".pxml"
                self.PagesImgName[pgNum] = os.path.join(inputdir, self.docdir, pgNum, self.inputdir_images, pgId + "_" + self.PagesImgResolutions[str(pgNum)] + ".png")
                if os.path.exists(self.PagesImgName[pgNum]):
                    self.PagesResolutionFactor[pgNum] = 1
                else:
                    self.PagesResolutionFactor[pgNum] = float(self.max_doc_resolution) / float(self.PagesImgResolutions[str(pgNum)])
                    self.PagesImgName[pgNum] = os.path.join(inputdir, self.docdir, pgNum, self.inputdir_images, pgId + "_" + str(self.max_doc_resolution) + ".png")
                    self.pxmlOutname[pgNum] = pgId + "_" + str(self.max_doc_resolution) + ".pxml"
            for entityElement in tree.xpath('//Entity'):
                entityId = entityElement.get("ID")
                pgIndex = entityElement.get("PAGE_NO")
                tocIndex = entityElement.get("FIRST_TOC_ENTRY_ID")
                self.EntitiesPage[entityId] = pgIndex
                self.EntitiesIndex[entityId] = tocIndex
            #---- READING PAGE FILES --------------------#
            count = 1
            while (count <= self.page_count):
                self.parse_legacy_page_data(str(count), self.PagesResolutionFactor[str(count)])
                count +=1  
            self.load_legacy_articles(self.input_pub_file_name)
            self.get_toc_article_types(self.input_pub_file_name)
        except Exception as e:
            print("ERROR in load_legacy_data for inputdir " + inputdir)
            print (e)
            print ("END ERROR \n\n")
            exit

    def pick_max_resolution(self, legacy_meta_file):
        try:
            tree = etree.parse(legacy_meta_file)
            resolution = 0
            for resElement in tree.xpath('//Resolution'):
                resText = resElement.text
                if int(resText) > resolution:
                    resolution = int(resText)
            self.max_doc_resolution = resolution
        except Exception as e:
            print("ERROR in pick_max_resolution " + legacy_meta_file)
            print (e)
            print ("END ERROR \n\n")
            sys.exit(1)


    #check if dir exists, creates it if not
    def prep_dir(self, out_dir):
        try:
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)
        except Exception as e:
            print("ERROR in prep_dir " + out_dir)
            print (e)
            print ("END ERROR \n\n")
            sys.exit(1)


    #parse Pg00x.xml file
    def parse_legacy_page_img_resolution(self, PgCount):
        try:
            tree = etree.parse(self.PagesXmlName[PgCount])
            MetaElement = tree.xpath('//XMD-PAGE/Meta')
            self.PagesImgResolutions[PgCount] = MetaElement[0].get("IMAGES_RESOLUTION")
        except Exception as e:
            print("ERROR in parse_legacy_page_img_resolution for page " + PgCount)
            print (e)
            print ("END ERROR \n\n")
            pass
 
    #parse Pg00x.xml file
    def parse_legacy_page_data(self, PgCount, resolution_factor):
        try:
            tree = etree.parse(self.PagesXmlName[PgCount])
            dir_path = (os.path.dirname(self.PagesXmlName[PgCount])) # dir of page file
            
            MetaElement = tree.xpath('//XMD-PAGE/Meta')

            self.PagesImgHeight[PgCount] = MetaElement[0].get("PAGE_HEIGHT")
            self.PagesImgWidth[PgCount] = MetaElement[0].get("PAGE_WIDTH")

            self.HeaderPrimitives
            for node in tree.xpath('//Primitive'): #all primitives needed
                content_id = node.get("ID")
                self.ContentPrimitives.append(content_id)
                
                content_seq = node.get("SEQ_NO") 
                content_id = node.get("ID")
                legacy_box = (self.get_correct_box_coordinates(content_id, dir_path, resolution_factor))
                left, bottom, right, top = legacy_box.split()
                coordinates = right + "," + top + " " + left + "," + top + " " + left + "," + bottom + " " + right + "," + bottom
                prim_type = node.get("ELEMENT_TYPE")
                if (prim_type != self.frame_primitive_type):
                    self.PrimitivesIndexInPage[content_id] = content_seq
                    self.PrimitiveTypes[content_id] = prim_type
                    self.RegionBoxing[content_id] = coordinates
                    if (prim_type == self.headline_primitive_type):
                        self.HeaderPrimitives.append(content_id)
            for header in self.HeaderPrimitives:
                if (self.PrimitivesIndexInPage[header] != "0"):
                    primitive_entity = header[:-2] #remove 2 last chars
                    self.PrimitivesIndexInPage[header] = "0"
                    for primitive in self.PrimitivesIndexInPage.keys():
                        if (primitive.startswith(primitive_entity) and (primitive != header)):
                            original_index = int(self.PrimitivesIndexInPage[primitive])
                            self.PrimitivesIndexInPage[primitive] = str(original_index + 1) #assuming headline had the last index
        except Exception as e:
            print("ERROR in parse_legacy_page_data for page " + PgCount)
            print (e)
            print ("END ERROR \n\n")
            pass
    
    #return the correct coordinate from ar00x file for every ar00?0? id
    def get_correct_box_coordinates(self, ar_id, path, resolution_factor): 
        file_name = ar_id[:-2]
        file_path = os.path.join(path, file_name)
        tree = etree.parse(file_path + ".xml")
        for node in tree.xpath('//Primitive'):
            if (node.get("ID")) == ar_id:
                return self.fix_factor(node.get("BOX"), resolution_factor)
        for node in tree.xpath('//Img'):
            if (node.get("ID")) == ar_id:
                return self.fix_factor(node.get("BOX"), resolution_factor)

    #In case image resolution is different that coordinates resolution
    def fix_factor(self, box, factor):
        try:
            coordinates = box.split(" ")
            for i in range(len(coordinates)):
                coordinates[i] = str(int( int(coordinates[i]) * factor))
            return " ".join(coordinates)
        except:
            print("fix_factor failed")
            return box
    
    def pxml_names_by_pgnum(self):
        return self.pxmlOutname

    def img_names_by_pgnum(self):
        imgOutname = {}
        for key, value in self.PagesImgName.items():
                imgOutname[key] = os.path.basename(value)
        return imgOutname

    #write TKBS xml for a page
    def write_transkribus_page_xml(self, pageCount):
        try:
            pgTarget = os.path.join(self.tkbs_exportdir, self.pxmlOutname[pageCount])
            attr_qname = etree.QName(self.tkbs_xsi, "schemaLocation")
            nsmap = {None: self.tkbs_xml_schema, \
                     "xsi": self.tkbs_xsi}
            root = etree.Element("PcGts", \
                     {attr_qname: self.tkbs_xml_schema + " " + self.tkbs_xsd}, \
                     nsmap=nsmap)
            doc = etree.ElementTree(root)
            Metadata = etree.SubElement(root, 'Metadata')
            Page = etree.SubElement(root, 'Page')
            Metadata.attrib['docId'] = self.doc_id
            Metadata.attrib['pageNr'] = str(pageCount)
            Metadata.attrib['pageId'] = self.doc_id + str(pageCount)
            Metadata.attrib['tsid'] = "2" + self.doc_id + str(pageCount)
            Page.attrib['imageHeight'] = self.PagesImgHeight[pageCount]
            Page.attrib['imageWidth'] = self.PagesImgWidth[pageCount]
            Page.attrib['imageFilename'] = os.path.basename(self.PagesImgName[pageCount])
            ReadingOrder = etree.SubElement(Page, 'ReadingOrder')
            OrderedGroup = etree.SubElement(ReadingOrder, 'OrderedGroup')
            OrderedGroup.attrib['caption'] = "Regions reading order"
            OrderedGroup.attrib['id'] = "ro_" + self.doc_id + str(pageCount)
            primitive_count = 0
            region_count = 0
            ePrimitives = {}
            for entity, tocIndex in self.EntitiesIndex.items():
                if self.EntitiesPage[entity] == str(pageCount):
                    ePrimitives = {}
                    for pkey, pvalue in self.PrimitivesIndexInPage.items():
                        if pkey.startswith(entity) and pkey in self.ContentPrimitives:
                            ePrimitives[pvalue] = pkey
                    ePrimitive_total = len(ePrimitives)
                    primitive_count = 0
                    while primitive_count <= (ePrimitive_total + 1):
                        if str(primitive_count) in ePrimitives:
                            rPrimitive = ePrimitives[str(primitive_count)]
                            pRaw = '<RegionRefIndexed regionRef="' + rPrimitive + '" index="' + str(region_count) + '"/>'
                            pNode = etree.fromstring(pRaw)
                            OrderedGroup.append(pNode)
                            RegionType = 'TextRegion'
                            if (self.PrimitiveTypes[rPrimitive] == self.graphic_primitive_type):
                                RegionType = 'GraphicRegion'
                            tRaw = '<' + RegionType + ' id="' + rPrimitive + \
                            '" custom="readingOrder {index:' + str(region_count) + ';}">' + \
                            '<Coords points="' + self.RegionBoxing[rPrimitive] + '"/>' + \
                            '</' + RegionType + '>'
                            tNode = etree.fromstring(tRaw)
                            if (self.PrimitiveTypes[rPrimitive] != self.graphic_primitive_type):
                                lastNode = etree.fromstring('<TextEquiv><Unicode/></TextEquiv>')
                                tNode.append(lastNode)
                            region_count = region_count + 1
                            Page.append(tNode)
                        primitive_count = primitive_count + 1
            doc.write(pgTarget)
        except Exception as e:
            print("ERROR in write_transkribus_page_xml for page number " + pageCount)
            print (e)
            print ("END ERROR \n\n")
            pass

    #copy images
    def copy_transkribus_images(self, outdir):
        try:
            for key, value in self.PagesImgName.items():
                target_file = os.path.join(outdir, os.path.basename(value))
                if not os.path.isfile(target_file):
                    copyfile(value, target_file)
        except Exception as e:
            print("ERROR in copy_transkribus_images " + outdir)
            print (e)
            print ("END ERROR \n\n")
            pass

    def export_tkbs_format(self, exportdir):
        try:
            self.tkbs_exportdir = exportdir
            self.prep_dir(self.tkbs_exportdir)
            self.copy_transkribus_images(self.tkbs_exportdir)# + "\\" + self.release_no)
            count = 1
            while (count <= self.page_count):
                #print("write_transkribus_page_xml " + str(count) + " of " + str(self.page_count))
                self.write_transkribus_page_xml(str(count))
                count = count + 1
        except Exception as e:
            print("ERROR in export_tkbs_format " + self.tkbs_exportdir)
            print (e)
            print ("END ERROR \n\n")
            pass

    def load_tkbs_data(self, docdir):
        self.tkbs_load_dir = docdir
        metafile = os.path.join(self.tkbs_load_dir, self.tkbs_meta_filename)
        if os.path.isfile(metafile):
            with open(metafile) as f:
                data = json.load(f)
                self.title = data["md"]["title"]
                self.colId = data["collection"]["colId"]
                self.colName = data["collection"]["colName"]
                self.docId = data["md"]["docId"]
                self.toolName = data["pageList"]["pages"][0]["tsList"]["transcripts"][0]["toolName"]
                for p in data["pageList"]["pages"]:
                    pnumber = p["pageNr"]
                    pxml = os.path.join(self.tkbs_load_dir, p["imgFileName"].replace(".png", ".pxml"))
                    if os.path.isfile(pxml):
                        self.pages[pnumber] = tkbs_page(pxml, pnumber, self.tkbs_xml_schema)

    def load_tkbs_page_ids(self, docjson):
        ids = {}
        for p in docjson["pageList"]["pages"]:
            pnumber = p["pageNr"]
            pid = p['pageId']
            ids[pnumber] = pid
        return ids

    def export_plaintext(self, outdir):
        try:
            self.prep_dir(outdir)
            with open(os.path.join(outdir, self.title + "_plaintext.txt"), mode = 'w', encoding = self.xmlcode) as o:
                for a in self.articles.values():
                    for r in a.article_regions.values():
                        o.write(r.text)
        except Exception as e:
            print("ERROR in export_plaintext " + outdir)
            print (e)
            print ("END ERROR \n\n")
            pass

    def match_legacy_articles(self):
        self.articles = {}
        for akey in self.legacy_articles:
            if akey in self.articles.keys():
                print("ERROR - article " + self.articles[akey].entity_primary + " already exists.")
            else:
                self.articles[akey] = tkbs_article(self.legacy_articles[akey].id,
                             None,
                             self.legacy_articles[akey].header_text,
                             self.legacy_articles[akey].primitive_primary,
                             self.legacy_articles[akey].entity_primary)
        for p in self.pages.values():
            for r in p.regions.values():
                reg_entity = r.id[0:-2] #cut last 2 chars
                isHeader = (r.id in self.HeaderPrimitives)
                for a in self.legacy_articles.values():
                    for e in a.entities.values():
                        if e.id == reg_entity:
                            readingorder = int(str(p.pagenumber) + str(r.readingorder))
                            self.articles[a.id].article_regions[readingorder] = r
                            if isHeader:
                                self.articles[a.id].header_region = r.id
                                self.articles[a.id].header = r.text


    def load_legacy_articles(self, metafile):
        if os.path.isfile(metafile):
            self.sourcefile = metafile
            tree = ET.parse(metafile)
            xroot = tree.getroot()
            self.legacy_articles = {}
            for a in xroot.findall("Logic_np/TOC_Entries/TOC_Entry"):
                aid = a.attrib["TOC_ENTRY_ID"]
                atitle = a.attrib["TITLE"]
                aprimitive = a.attrib["PRIM_ID_REF"]
                aentity = a.attrib["ENTITY_ID_REF"]
                self.legacy_articles[aid] = legacy_article(aid, atitle, aprimitive, aentity)
            for s in xroot.findall("Body_np/Section"):
                for p in s.findall("Page"):
                    for e in p.findall("Entity"):
                        eid = e.attrib["ID"]
                        eentry = e.attrib["FIRST_TOC_ENTRY_ID"]
                        if eentry in self.legacy_articles.keys():
                            self.legacy_articles[eentry].entities[eid] = legacy_entity(eid)
                        else:
                            print("Warning TOC ENTRY ID " + eentry + " MISSING in " + metafile)


    def export_csv_by_line(self, outdir):
        try:
            self.prep_dir(outdir)
            with open(os.path.join(outdir, self.title + ".csv"), mode = 'w', encoding = self.xmlcode, newline='') as o:
            #with open(os.path.join(outdir, self.title + ".csv"), mode = 'wb') as o:
                fieldnames = ['article_id', 'headline', 'region_id', 'page_id', 'line_id', 'text']
                writer = csv.DictWriter(o, fieldnames=fieldnames)
                writer.writeheader()
                for a in self.articles.keys():
                    aid = self.articles[a].id
                    header = self.articles[a].header
                    for r in self.articles[a].article_regions.keys():
                        rid = self.articles[a].article_regions[r].id
                        pid = self.articles[a].article_regions[r].pagenumber
                        for l in self.articles[a].article_regions[r].lines.keys():
                            lids = str(self.articles[a].article_regions[r].lines[l].id).split('l')
                            lid = lids[len(lids)-1]
                            writer.writerow({'article_id': str(aid), 'headline': header, 'region_id': str(rid), 'page_id': str(pid), 'line_id': str(lid), 'text': self.articles[a].article_regions[r].lines[l].text})
                            #o.write("%s,%s,%s,%s,%s\n" %(aid, rid, pid, lid, f'{self.articles[a].article_regions[r].lines[l].text}'))
        except Exception as e:
            print("ERROR in export_csv " + outdir)
            print (e)
            print ("END ERROR \n\n")
            pass

    def export_csv_regions(self, outdir):
        try:
            self.prep_dir(outdir)
            with open(os.path.join(outdir, self.title + ".csv"), mode = 'w', encoding = self.xmlcode, newline='') as o:
            #with open(os.path.join(outdir, self.title + ".csv"), mode = 'wb') as o:
                fieldnames = ['article_id', 'headline', 'region_id', 'page_id', 'text']
                writer = csv.DictWriter(o, fieldnames=fieldnames)
                writer.writeheader()
                for a in self.articles.keys():
                    aid = self.articles[a].id
                    header = self.articles[a].header
                    for r in self.articles[a].article_regions.keys():
                        region_text = ""
                        rid = self.articles[a].article_regions[r].id
                        pid = self.articles[a].article_regions[r].pagenumber
                        for l in self.articles[a].article_regions[r].lines.keys():
                            region_text = " ".join([region_text, self.articles[a].article_regions[r].lines[l].text])
                        writer.writerow({'article_id': str(aid), 'headline': header, 'region_id': str(rid), 'page_id': str(pid), 'text': region_text})

        except Exception as e:
            print("ERROR in export_csv " + outdir)
            print (e)
            print ("END ERROR \n\n")
            pass


    def export_csv_articles(self, outdir):
        try:
            self.prep_dir(outdir)
            with open(os.path.join(outdir, self.title + ".csv"), mode = 'w', encoding = self.xmlcode, newline='') as o:
            #with open(os.path.join(outdir, self.title + ".csv"), mode = 'wb') as o:
                fieldnames = ['article_id', 'headline', 'text']
                writer = csv.DictWriter(o, fieldnames=fieldnames)
                writer.writeheader()
                for a in self.articles.keys():
                    articletext = ""
                    aid = self.title + "_" + self.article_types[a] + "_" + self.articles[a].id
                    header = self.articles[a].header
                    for r in self.articles[a].article_regions.keys():
                        for l in self.articles[a].article_regions[r].lines.keys():
                            articletext = " ".join([articletext, self.articles[a].article_regions[r].lines[l].text])
                    writer.writerow({'article_id': str(aid), 'headline': header, 'text': articletext})
        except Exception as e:
            print("ERROR in export_csv " + outdir)
            print (e)
            print ("END ERROR \n\n")
            pass

    def export_plaintext_articles(self, outdir):
        try:
            self.prep_dir(outdir)
            for a in self.articles.keys():
                with open(os.path.join(outdir, self.title + "_" + self.article_types[a] + "_" + str(a) + "_plaintext.txt"), mode = 'w', encoding = self.xmlcode) as o:
                    for r in self.articles[a].article_regions.values():
                        o.write(r.text)
        except Exception as e:
            print("ERROR in export_plaintext " + outdir)
            print (e)
            print ("END ERROR \n\n")
            pass

    def export_tei(self, outdirectory):
        try:
            TEI = ET.Element("TEI", attrib = {"xmlns": "http://www.tei-c.org/ns/1.0", "style": "direction:rtl; unicode-bidi:embed"})
            #------ meta data -------------------------------
            header = ET.SubElement(TEI, "teiHeader")
            fileDesc = ET.SubElement(header, "fileDesc")
            titleStmt = ET.SubElement(fileDesc, "titleStmt")
            ET.SubElement(titleStmt, "title").text = self.doc_title
            publicationStmt = ET.SubElement(fileDesc, "publicationStmt")
            ET.SubElement(publicationStmt, "p").text = "HAZFIRAH - NLI Olive data combined with Transkribus OCR by OMILAB sinai.rusinek@mail.huji.ac.il"
            sourceDesc = ET.SubElement(fileDesc, "sourceDesc")
            ET.SubElement(sourceDesc, "bibl").text = "TKBS Collection: " + str(self.colId) + " " + self.colName + ", Document: " + str(self.docId) + ", Tool: " + self.toolName
            #----- facs physical copy data -------------------
            facs = {}
            surface = {}
            graphic = {}
            zones = {}
            for p in self.pages:
                facs[p] = ET.SubElement(TEI, "facsimile", attrib = {"xml:id": "page_" + str(p)})
                surface[p] = ET.SubElement(facs[p], "surface")
                graphic[p] = ET.SubElement(surface[p], "graphic", attrib = {"height": self.pages[p].imageHeight + "px", 
                       "width": self.pages[p].imageWidth + "px", 
                       "url": self.pages[p].imageFilename})
                for r in self.pages[p].regions:
                    rid = self.pages[p].regions[r].id
                    zones[rid] = ET.SubElement(surface[p], 
                         "zone", 
                         attrib = {"xml:id": rid, 
                                   "rendition": "TextRegion", 
                                   "points": self.pages[p].regions[r].coordinates})
                    for l in self.pages[p].regions[r].lines:
                        lid = self.pages[p].regions[r].lines[l].id
                        zones[lid] = ET.SubElement(zones[rid], 
                            "zone", 
                            attrib = {"xml:id": lid, 
                                   "rendition": "Line", 
                                   "points": self.pages[p].regions[r].lines[l].coordinates.get("points")}) #line coordinates
            #-------- data -----------------------------------
            text = ET.SubElement(TEI, "text")
            body = ET.SubElement(text, "body")
            current_page = 0
            pages = {} #page beginnings
            divs = {} #articles
            heads = {} #titles
            p = {} #regions / primitives
            for a in self.articles:
                a_id = self.articles[a].id
                if current_page == 0:
                    pages[1] = ET.SubElement(body, "pb", attrib = {"n": "1", "facs": "page_1"})
                    current_page = 1
                divs[a_id] = ET.SubElement(body, "div", attrib = {"xml:id": a_id})
                heads[a_id] = ET.SubElement(divs[a_id], "head").text = self.articles[a].header #TBD
                for r in self.articles[a].article_regions:
                    r_id = self.articles[a].article_regions[r].id
                    r_page = self.articles[a].article_regions[r].pagenumber
                    if current_page != r_page:
                        pages[r_page] = ET.SubElement(body, "pb", attrib = {"n": str(r_page), "facs": "page_" + str(r_page)})
                        current_page = r_page
                    p_text_with_floating_tags = ""
                    for l in self.articles[a].article_regions[r].lines:
                        l_id = self.articles[a].article_regions[r].lines[l].id
                        #lb[l_id] = ET.SubElement(p[r_id], "lb", attrib = {"facs": l_id}).text = self.articles[a].article_regions[r].lines[l].text #TBD
                        p_text_with_floating_tags += self.articles[a].article_regions[r].lines[l].text + \
                        '\n<lb facs=' + '"' + l_id + '"' + '/>'
                    p_text_with_floating_tags = '<p>' + p_text_with_floating_tags + '</p>'
                    p[r_id] = ET.fromstring(p_text_with_floating_tags)
                    p[r_id].set("facs", r_id)
                    divs[a_id].append(p[r_id])
            tree = ET.ElementTree(TEI)
            tree.write(os.path.join(outdirectory, self.title + "_tei.xml"), encoding="UTF-8", xml_declaration=True)
        except Exception as e:
            print("ERROR in export_tei " + outdirectory)
            print (e)
            print ("END ERROR \n\n")
            pass
        
class tkbs_page:

    def __init__(self, pgxml, number, schema):
        try:
            
            if os.path.isfile(pgxml):
                self.pagenumber = number
                self.sourcefile = pgxml
                tree = ET.parse(pgxml)
                xroot = tree.getroot()
                for p in xroot.findall('{' + schema + '}Page'):
                    self.imageFilename = p.attrib["imageFilename"]
                    self.imageWidth = p.attrib["imageWidth"]
                    self.imageHeight = p.attrib["imageHeight"]
                    self.regions = {}
                    ro = p.find('{' + schema + '}ReadingOrder')
                    og = ro.find('{' + schema + '}OrderedGroup')
                    for rr in og.findall('{' + schema + '}RegionRefIndexed'):
                        i = rr.attrib["index"]
                        r = rr.attrib["regionRef"]
                        self.regions[r] = tkbs_region(r, i, number)
                    for tr in p.findall('{' + schema + '}TextRegion'):
                        i = tr.attrib["id"]
                        coo = tr.find('{' + schema + '}Coords')
                        self.regions[i].coordinates = coo.attrib["points"]
                        tx = tr.find('{' + schema + '}TextEquiv')
                        ucode = tx.find('{' + schema + '}Unicode')
                        if str(ucode.text).upper() != "NONE":
                            self.regions[i].text = ucode.text
                        for l in tr.findall('{' + schema + '}TextLine'):
                            lcoo = l.find('{' + schema + '}Coords')
                            lid = l.attrib["id"]
                            ltx = l.find('{' + schema + '}TextEquiv')
                            lucode = ltx.find('{' + schema + '}Unicode')
                            lindex = l.attrib["custom"].split(":")[1].split(";")[0]
                            ltext = ""
                            if str(lucode.text).upper() != "NONE":
                                ltext = lucode.text
                            self.regions[i].lines[lid] = tkbs_line(lid, lindex, lcoo, ltext)
        except Exception as e: 
            print("ERROR in tkbs_page " + pgxml + " with schema " + schema)
            print (e)
            print ("END ERROR \n\n")
            raise e
    
            
            
class tkbs_line:

    def __init__(self, id, order, coords, text):
        self.id = id
        self.index = order
        self.coordinates = coords
        self.text = text

class tkbs_region:

    def __init__(self, regid, regindex, page):
        self.id = regid
        self.pagenumber = page
        self.readingorder = regindex
        self.coordinates = ""
        self.text = ""
        self.lines = {}

class tkbs_article:

    def __init__(self, toc_entry_id, header_region, header, primitive_primary, entity_primary):
        self.id = "toc_" + toc_entry_id
        self.header_region = header_region
        self.header = header
        self.primitive_primary = primitive_primary
        self.entity_primary = entity_primary
        self.article_regions = {}

class legacy_article:

    def __init__(self, toc_entry_id, header_text, primitive_primary, entity_primary):
        self.id = toc_entry_id
        self.header_text = header_text
        self.primitive_primary = primitive_primary
        self.entity_primary = entity_primary
        self.entities = {}

class legacy_entity:

    def __init__(self, entity_id):
        self.id = entity_id

def locate_legacy(doc, topdir):
    bytespub = bytes(doc, 'utf-8')
    for root, dirs, files in os.walk(topdir):
        for fname in files:
            if fname.upper().endswith("TOC.XML"):
                fullname = os.path.join(root, fname)
                with open(fullname, 'rb', 0) as file, mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as s:
                    if s.find(bytespub) != -1:
                        return fullname

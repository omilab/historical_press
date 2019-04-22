# -*- coding: utf-8 -*-
"""

OMILAB 2019
Convert Olive-Abbyy historical press publication format to Transkribus page-xml format, excluding word boxing and text.

"""

from lxml import etree
from shutil import copyfile
import os, sys

class Publication:
    
    def __init__(self):
        self.doc_id = None #from TOC.xml
        self.doc_title = None # from TOC.xml
        self.release_no = None #from TOC.xml
        self.toc = "TOC.xml"
        self.docdir = "Document"
        self.abydir = None
        self.tkbs_exportdir = None
        self.page_count = 0
        self.PagesImgName = {} #key: page num, value: image filename, from TOC.xml
        self.PagesXmlName = {} #key: page num, value: Pg00x.xml filename, from TOC.xml
        self.EntitiesIndex = {} #key: Entity name, from TOC.xml, value:   entity TOC_ENTRY_ID
        self.EntitiesPage = {} #key: Entity name, value: entity PAGE_NO , from TOC.xml
        self.input_pub_file_name = ""
        self.factor1 = 1.7238
        self.factor2 = 0.67
        self.xmlcode = "UTF-8"
        self.cut_low_line_part = 0.33 #remove the lower part of the line box to help TKBS identify the baseline
        self.headline_primitive_type = 'HedLine_hl1'
        self.frame_primitive_type = 'AdFrame'
        self.graphic_primitive_type = 'Picture'
        self.inputdir_images = 'Img'
        self.outputdir_xmls = 'page'
        #resolution_filename_part144 = "_144"
        self.resolution_filename_part = "_150"
        self.abby_garbage_width = 13
        self.factor1_144 = 1.7237
        self.factor2_144 = 0.494
        self.resolution_144 = "_144"
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

    #remove garbage lines by identifying lines with very small width    
    def is_garbage_line(self, linebox):
        try:
            xleft, ybottom, xright, ytop = linebox.split()
            line_width = int(xright) - int(xleft)
            if line_width <= self.abby_garbage_width:
                return True
            else:
                return False
        except Exception as e:
            print("ERROR in is_garbage_line " + str(linebox))
            print (e)
            print ("END ERROR \n\n")
            return False
            pass

    #read Arxxx.xml file
    def get_aby_entity_data(self, input_file_name):
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
                    abby_box = line_child.get("BOX")
                    if not self.is_garbage_line(abby_box):
                        line_box = self.calc_coordinates(self.modify_abby_line_box(abby_box, self.cut_low_line_part), self.factor1, self.factor2)
                        self.LineIndexInRegion[line_id] = line_seq
                        self.LineBoxing[line_id] = line_box
                        count = count + 1
        except Exception as e: 
            print("ERROR in get_aby_entity_data " + input_file_name)
            print (e)
            print ("END ERROR \n\n")
            pass
        
    def load_aby_data(self, inputdir):
        try:
            #---- READING TOC FILE --------------------#
            self.abydir = inputdir
            self.pick_resolution()
            self.input_pub_file_name = os.path.join(self.abydir, self.toc)
            #global EntityHasHeader
            tree = etree.parse(self.input_pub_file_name)
            MetaElement = tree.xpath('//Xmd_toc')
            self.release_no = MetaElement[0].get("RELEASE_NO")
            release_parts = self.release_no.split("-")
            self.doc_id = release_parts[2] + release_parts[3] + release_parts[4]
            self.doc_title = release_parts[1] + "-"+ release_parts[2] +"-"+ release_parts[3] +"-"+ release_parts[4]
            self.page_count = len(tree.xpath('//Page'))
            for pgElement in tree.xpath('//Page'):
                pgNum = pgElement.get("PAGE_NO")
                pgImage = pgElement.get("ID") + self.resolution_filename_part + ".png"
                pxmlOutname = pgElement.get("ID") + self.resolution_filename_part + ".pxml"
                pgXml = pgElement.get("ID") + ".xml"
                self.PagesImgName[pgNum] = inputdir + self.docdir + "\\" + pgNum + "\\" + self.inputdir_images + "\\" + pgImage
                self.PagesXmlName[pgNum] = inputdir + self.docdir + "\\" + pgNum + "\\" + pgXml
                self.pxmlOutname[pgNum] = pxmlOutname
            for entityElement in tree.xpath('//Entity'):
                entityId = entityElement.get("ID")
                pgIndex = entityElement.get("PAGE_NO")
                tocIndex = entityElement.get("FIRST_TOC_ENTRY_ID")
                self.EntitiesPage[entityId] = pgIndex
                self.EntitiesIndex[entityId] = tocIndex
            #---- READING PAGE FILES --------------------# 
            count = 1
            while (count <= self.page_count):
                pagedir = self.abydir + "\\" + self.docdir + "\\" + str(count)
                self.parse_aby_page_data(str(count))
                #follow a single page entities xml list
                for root, dirs, files in os.walk(pagedir):
                    for fname in files:
                        if (fname.upper().endswith("XML") and not fname.upper().startswith("P")):
                            self.get_aby_entity_data(os.path.join(root, fname))
                count +=1
        except Exception as e: 
            print("ERROR in load_aby_data for inputdir " + inputdir)
            print (e)
            print ("END ERROR \n\n")
            exit

    #scan was done with 2 different resolutions, identify and change factors accordingly
    def pick_resolution(self):
        for root, dirs, files in os.walk(self.abydir):
            for fname in files:
                if fname.upper().endswith(self.resolution_144 + ".PNG"):
                    self.resolution_filename_part = self.resolution_144
                    self.factor1 = self.factor1_144
                    self.factor2 = self.factor2_144
                    print("converted to " + self.resolution_144)
                    return

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

    #use a factor to get a number converted to Transkribus standard, return it as a truncated string
    def calc_h_w_coordinate(self, incoord, coeff1):
        try:
            return str(int(round(int(incoord)*coeff1, 0)))
        except Exception as e:
            print("ERROR in calc_h_w_coordinate ")
            print (e)
            print ("END ERROR \n\n")
            pass
    
    #use factors to get a number converted to Transkribus standard, return it as a truncated string
    def calc_one_coordinate(self, incoord, coeff1, coeff2):
        try:
            return str(int(round(int(incoord)*coeff1*coeff2, 0)))
        except Exception as e:
            print("ERROR in calc_one_coordinate ")
            print (e)
            print ("END ERROR \n\n")
            pass
    
    #truncate lower third of each line to improve TKBS work to create baseline        
    def modify_abby_line_box(self, box, cut_part):
        try:
            xleft, ybottom, xright, ytop = box.split()
            new_top = str(int(round(int(ytop) - cut_part*(int(ytop) - int(ybottom)))))
            modified_box = xleft + " " + ybottom + " " + xright + " " + new_top
            return modified_box
        except Exception as e:
            print("ERROR in modify_abby_line_box " + box + " cut part: " + cut_part)
            print (e)
            print ("END ERROR \n\n")
            pass
        
    #combine 4 converted vars of a Box to Transkribux x,y Box style, return the combined string    
    def calc_coordinates(self, abby_box, coef1, coef2):
        try:
            xleft, ybottom, xright, ytop = abby_box.split()
            left = self.calc_one_coordinate(xleft, coef1, coef2)
            bottom = self.calc_one_coordinate(ybottom, coef1, coef2)
            right = self.calc_one_coordinate(xright, coef1, coef2)
            top = self.calc_one_coordinate(ytop, coef1, coef2)
            coordinates = right + "," + top + " " + left + "," + top + " " + left + "," + bottom + " " + right + "," + bottom
            return coordinates
        except Exception as e:
            print("ERROR in calc_coordinates " + left + " " + bottom + " " + right + " " + top)
            print (e)
            print ("END ERROR \n\n")
            pass
    
    #combine 4 converted vars of a Box to Transkribux x,y Box style, return the combined string    
    def calc_Pg_coordinates(self, abby_box, coef1):
        try:
            xleft, ybottom, xright, ytop = abby_box.split()
            left = self.calc_h_w_coordinate(xleft, coef1)
            bottom = self.calc_h_w_coordinate(ybottom, coef1)
            right = self.calc_h_w_coordinate(xright, coef1)
            top = self.calc_h_w_coordinate(ytop, coef1)
            coordinates = right + "," + top + " " + left + "," + top + " " + left + "," + bottom + " " + right + "," + bottom
            return coordinates
        except Exception as e:
            print("ERROR in calc_Pg_coordinates " + left + " " + bottom + " " + right + " " + top)
            print (e)
            print ("END ERROR \n\n")
            pass

    #parse Pg00x.xml file
    def parse_aby_page_data(self, PgCount):
        try:
            tree = etree.parse(self.PagesXmlName[PgCount])
            MetaElement = tree.xpath('//XMD-PAGE/Meta')
            self.PagesImgHeight[PgCount] = self.calc_h_w_coordinate(MetaElement[0].get("PAGE_HEIGHT"), self.factor1)
            self.PagesImgWidth[PgCount] = self.calc_h_w_coordinate(MetaElement[0].get("PAGE_WIDTH"), self.factor1)
            HeaderPrimitives = [] #key: entity id, value: bool true if entity has HeadLine_hl1 primitive
            for node in tree.xpath('//Primitive'): #all primitives needed
                content_id = node.get("ID")
                self.ContentPrimitives.append(content_id)
                content_seq = node.get("SEQ_NO")
                content_box = node.get("BOX")
                prim_type = node.get("ELEMENT_TYPE")
                if (prim_type != self.frame_primitive_type):
                    self.PrimitivesIndexInPage[content_id] = content_seq
                    self.PrimitiveTypes[content_id] = prim_type
                    self.RegionBoxing[content_id] = self.calc_Pg_coordinates(content_box, self.factor1)
                    if (prim_type == self.headline_primitive_type):
                        HeaderPrimitives.append(content_id)
            for header in HeaderPrimitives:
                if (self.PrimitivesIndexInPage[header] != "0"):
                    primitive_entity = header[:-2] #remove 2 last chars
                    self.PrimitivesIndexInPage[header] = "0"
                    for primitive in self.PrimitivesIndexInPage.keys():
                        if (primitive.startswith(primitive_entity) and (primitive != header)):
                            original_index = int(self.PrimitivesIndexInPage[primitive])
                            self.PrimitivesIndexInPage[primitive] = str(original_index + 1) #assuming headline had the last index
        except Exception as e:
            print("ERROR in parse_aby_page_data " + PgCount)
            print (e)
            print ("END ERROR \n\n")
            pass        

    #write TKBS xml for a page   
    def write_transkribus_page_xml(self, pageCount):
        try:
            pgTarget = self.tkbs_exportdir + "\\" + self.pxmlOutname[pageCount]
            
            attr_qname = etree.QName("http://www.w3.org/2001/XMLSchema-instance", "schemaLocation")
            nsmap = {None: "http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15", \
                     "xsi": "http://www.w3.org/2001/XMLSchema-instance"}

            root = etree.Element("PcGts", \
                     {attr_qname: "http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15 http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15/pagecontent.xsd"}, \
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
                                for tkey, tvalue in self.LineIndexInRegion.items():
                                    if tkey.startswith(rPrimitive):
                                        lindex = tvalue - 1
                                        lRaw = '<TextLine id="line_' + tkey + '" custom="readingOrder {index:' + str(lindex) + ';}">' + \
                                        '<Coords points="' + self.LineBoxing[tkey] + '"/>' + \
                                        '</TextLine>'
                                        lNode = etree.fromstring(lRaw)
                                        lastNode = etree.fromstring('<TextEquiv><Unicode/></TextEquiv>')
                                        lNode.append(lastNode)
                                        tNode.append(lNode)
                                lastNode = etree.fromstring('<TextEquiv><Unicode/></TextEquiv>')
                                tNode.append(lastNode)
                            region_count = region_count + 1
                            Page.append(tNode)
                        primitive_count = primitive_count + 1
            doc.write(pgTarget)
        except Exception as e: 
            print("ERROR in write_transkribus_page_xml " + pageCount)
            print (e)
            print ("END ERROR \n\n")
            pass            

    #copy images    
    def copy_transkribus_images(self, outdir):
        try:
            for key, value in self.PagesImgName.items():
                target_file = outdir + "\\" + os.path.basename(value)
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
        
''' TEST
p = Publication()
p.load_aby_data("C:\\test\\0105\\")
p.export_tkbs_format("C:\\test\\0105_out\\")
'''


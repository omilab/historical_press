# HOP  (Historical OCR Pipeline)
## Introduction
HOP is a tool that can massively handle legacy products of various OCR systems, such as Olive Software's system products and bring more accurate OCR using [Transkribus](https://transkribus.eu/Transkribus/). It is a pipeline that transforms PRXML files via Transkribus into a research corpus,  and deals with the challenge of improving the OCR without losing the valuable work that was done hitherto to analyze the layout and content structure of the newspapers. 
for this we created an workflow which converts the legacy format to an open format, on which the improved text recognition technologies can run to produce improved output that meets the threshold and requirements of text analytical research.

The pipeline consists of three subsequent but independent stages: 
- In part one, the pipeline gets PRXML files and images as input, and converts their region segmentation data  into the open PAGE.XML format (see also road map 1 below).
- The second part uploads the files to Transkribus using its API. In Trankribus, line detection and text recognition are preformed and the resulting product is a better OCR text, framed in the original text regions.
- The third part takes Transkribus' output and migrates it to several formats that facilitate text analytical methods: plain text files, XML-TEI, and tabular data in TSV files (see also road map 2 below).


## Getting started

### Prerequisites
- Python 3 or Python 2.7
- Username in Transkribus
- HTR model in Transkribus (for Hebrew 19th century press, we used 'OMILab')
- Layout analysis line detection model (e.g. Preset)

##### Notes on using Transkribus' services:
Around June 2020 Transkribus  will be available as payed service, in the framework of the READ Coop:  https://read.transkribus.eu/coop/. 


### Directoy structure
For proper system operation, make sure the folder structure is as described below:
A Newspaper folder that includes:
  * TOC.xml file
  * Documnet folder that includes:
        * PDF of the newspaper issue
        * A Folder for every newspaper page that includes:
          * PgXXX.xml (where XXX is the page number; this file include a strcuctural inforamtion about this page)
          * ArYYY.xml for every article in this page (where YYY is the article number like that appears in the PgXXX.xml file; this file include a strcuctural inforamtion about this article)
          * AdYYY.xml for every advertisement in this page (where YYY is the advertisement number like that appears in the PgXXX.xml file; this file include a strcuctural inforamtion about this advertisement)
          * Img folder that includes images of all the objects in the page together and alone.

## Tutorial
It should be noted that the parts are not interdependent. Although they are part of one pipeline, only the relevant stages can be used without any particular problem.
### Part 1 - Legacy format to Transkribus format converter
This script allows the user to convert directories from the legacy format into the PAGE.XML files that can be uploaded later into Transkribus or used in another way.

For the demo, we will use the directory "resources_for_tests" which included in the repo. 
You will see that the directory structure is like the description above.

Execute the script "legacy_to_tkbs_format_converter.py" via command line (or any other way you choose). Now, you'll be asked to insert the path of the  directory that you want to convert. You can choose a parent folder, and all the sub-folders will be converted.
![insert path please](https://github.com/yanirmr/historical_press/blob/master/OCR_Pipeline/images_for_tutorial/tutorial1.JPG)

In our case we will take "resources_for_tests":
![resources_for_tests](https://github.com/yanirmr/historical_press/blob/master/OCR_Pipeline/images_for_tutorial/tutorial2.JPG)

After the script will be executed (it supposed to be very quickly - less than one second per folder; depending on size, of course). You should get succesful response that containing an update on the number of successfully converted folders and where to find them now.
![succesful response](https://github.com/yanirmr/historical_press/blob/master/OCR_Pipeline/images_for_tutorial/tutorial3.JPG)
### Part 2 - Work with Transkribus' API

With this part of the script you will upload your data to the Transkribus server, run layout analysis and your chosen HTR model. When running the script "tkbs_uploader.py" you will be prompted to insert:
* your transkribus username
* your transkribus password
* source path (use the same path you used for the first stage to work on the results of the conversion from legacy files)
* the id of the collection in Transkribus where you would like to store the newspaper issues.
* the id of the HTR model
For convenience sake you can skip these stages by saving a file titled conf.json in the folder which includes this information:
{
    "username": "someone@email",
    "password": "whichever",
    "src_path": "/Users/...",
    "collection_id": id_number,
    "htr_model_id": id_number,
    "dst_path": "/Users/...",
    "line_detection": "yes"
}

    
## Roadmap
1.Currently, part 1 of the pipeline converts the text regions from the legacy files into the PAGE.XML files, and uses other structural information - the order and structure types (Advertisements, Heads) - for the post processing. Further development will add a conversion of this information directly into the page.xml as custom attribute values of text regions.
2.In order to avail the output to external viewers the PAGE.XML will have to be converted to the viewer's input formats (e.g., METZ @ ALTO#)

## Authors
This project was initiated and created by [OMILab](https://www.openu.ac.il/en/omilab).

[OmiLab’s project on Historical Newspaper Archive Research](https://www.openu.ac.il/en/omilab/pages/historicalnewspaper.aspx) is run in collaboration with the [Historical Jewish Press project](https://web.nli.org.il/sites/JPress/English) of the Tel Aviv University and the National Library of Israel.  [The National Library of Israel (https://web.nli.org.il/sites/nli/english/pages/default.aspx)] provided access to selected image and OCR output files at the back end of JPRESS. 

## License
<img src="https://github.com/yanirmr/historical_press/blob/master/OCR_Pipeline/images_for_tutorial/CC-BY-SA_icon.svg.png" width="200" height="50" />

The code is licensed under a [Creative Commons Attribution-Share Alike 3.0](https://creativecommons.org/licenses/by-sa/4.0/). You are welcome to copy and redistribute the material in any medium or format, remix, transform, and build upon the material for any purpose, even commercially,  as long as you give appropriate credit to OMILab, provide a link to the license,  indicate if changes were made and distribute your contributions under the same license as the original. 

## Related projects
- [Transkribus Project](https://github.com/Transkribus)

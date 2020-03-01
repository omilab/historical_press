# HOP  (Historical OCR Pipeline)
## Introduction
HOP is a pipeline that transform prxml via [Transkribus](https://transkribus.eu/Transkribus/) to research corpus.
The pipeline get prxml files and text images as an input, convert them and upload to Transkribus. Then, the workflow in Transkribus done (lines segmentation, OCR etc.) and the resulting product is better OCR text for further analysis.

It is a tool that can massively handle legacy products of various OCR systems, such as Olive Software's system products and bring more accurate OCR using Transkribus. In detail, the challenge the tool deal with is enable improving the OCR without losing the valuable work that was done to analyze the layout and content structure of the newspapers; for this we created an open workflow which migrates legacy segmentation data into the open Page format, on which the improved text recognition technologies can run, and then outputs the data as a TEI-XML encoded and enriched corpus.

## Getting started

### Prerequisites
- Python 3 or Python 2.7
- Username in Transkribus
- HTR model in Transkribus (for Hebrew 19th century press, we used 'OMILab')
- Layout analysis line detection model (e.g. Preset)

##### Notes on using in Transkribus
Around June 2020 Transkribus  will be available as payed service, in the framework of the READ Coop:https://read.transkribus.eu/coop/ 


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

## Roadmap
Currently, part 1 of the pipeline converts the text regions from the legacy files into the PAGE.XML files, and uses other structural information - the order and structure types (Advertisements, Heads) - for the post processing. We plan to add a conversion of this information directly into the page.xml as custom attribute values of text regions.


## Authors
This project was initiated and created by [OMILab](https://www.openu.ac.il/en/omilab).

[OmiLab’s project on Historical Newspaper Archive Research](https://www.openu.ac.il/en/omilab/pages/historicalnewspaper.aspx) is run in collaboration with the [Historical Jewish Press collection](https://web.nli.org.il/sites/JPress/English) of the Tel Aviv University and the National Library of Israel, that provided access to selected image and OCR output files at the back end of JPRESS 

## License
The code is licensed under a [Creative Commons Attribution-Share Alike 3. 0] (https://creativecommons.org/licenses/by-sa/4.0/). You are welcome to copy and redistribute the material in any medium or format, remix, transform, and build upon the material for any purpose, even commercially,  as long as you give appropriate credit to OMILab, provide a link to the license,  indicate if changes were made and distribute your contributions under the same license as the original. 

## Related projects
- [Transkribus Project](https://github.com/Transkribus)

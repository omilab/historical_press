# project title  (short and sweet name)
## Introduction
X is a pipeline that transform prxml via [Transkribus](https://transkribus.eu/Transkribus/) to research corpus.
The pipeline get prxml files and text images as an input, convert them and upload to Transkribus. Then, the workflow in Transkribus done (lines segmentation, OCR etc.) and the resulting product is better OCR text for further analysis.

It is a tool that can massively handle legacy products of various OCR systems, such as Olive Software's system products and bring more accurate OCR using Transkribus. In detail, the challenge the tool deal with is enable improving the OCR without losing the valuable work that was done to analyze the layout and content structure of the newspapers; for this we created an open workflow which migrates legacy segmentation data into the open Page format, on which the improved text recognition technologies can run, and then outputs the data as a TEI-XML encoded and enriched corpus.

## Getting started

### Prerequisites
- Python 3 or Python 2.7
- Username in Transkribus
- OCR model in Transkribus

### Directoy structure

## Tutorial

## Roadmap

## Authors
This project intiated and created by [OMILab](https://www.openu.ac.il/en/omilab).

[OmiLab’s project on Historical Newspaper Archive Research](https://www.openu.ac.il/en/omilab/pages/historicalnewspaper.aspx) is run in collaboration with the National Library of Israel, that provided access to selected image and OCR output files at the back end of JPRESS - the Historical Jewish Press collection of the Tel Aviv University and the National Library of Israel.


## Contribute
Please read CONTRIBUTING.md for details on our code of conduct, and the process for submitting pull requests to us.

## License


## Related projects
- [Transkribus Project](https://github.com/Transkribus)
- [Pocoto](https://github.com/cisocrgroup/PoCoTo)

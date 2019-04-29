# Historical newspaper archive research at OMILab
https://www.openu.ac.il/en/omilab

OmiLab’s project on Historical Newspaper Archive Research is run in collaboration with the National Library of Israel, that provided access to selected image and OCR output files at the back end of JPRESS - the Historical Jewish Press collection of the Tel Aviv University and the National Library of Israel. As a pilot study we chose HaZefirah, which started 1862 in Warsaw as a weekly publication, and in 1886 became the first daily newspaper in the Hebrew language. Over decades of its publication it changed editorship, places of publication, formats, genres and ideologies and therefore makes for a fascinating case for ‘distant reading’ approaches. 

Worldwide, large historical newspapers digitization project provide oceans of valuable historical periodical data. Much of this data, however, is available in platforms that provide mediocre OCR, which hinders  the application of text analytical methods of distant reading, NLP, NER and various methods of semantic processing. 

In the first phase, we use machine learning based tools through the platform Transkribus to train a model for historical Hebrew print, improving significantly both line detection and character recognition. Our next challenge was to enable improving the OCR without losing the valuable work that was done to analyze the layout and content structure of the newspapers; for this we created an open workflow which migrates legacy segmentation data  into the open Page format, on which the improved text recognition technologies can run, and then outputs the data as a TEI-XML encoded and enriched corpus.


 We are currently  experimenting with various analysis research pivots: named entity extraction, geo-temporal examination, keyword analysis over time and topic modelling. 
The project will not only enable thorough digital research of the fascinating corpus of HaZefirah but will serve as a proof-of-concept study for any future endeavour to salvage 315 other titles, entailing over two million pages, in the Jewish Historical Press collection of JPRESS. The workflow can also be adopted by hundreds of digital collections which are in similar condition. 


## Legacy to PAGE Pipeline
The folder "OCR_Pipeline" contains a Jupyter notebook: Pipeline.ipynb.
The notebook describes the pipeline steps and includes usage samples. To use the samples, import 2 python files that are also  included: TkbsApiClient.py and TkbsPublication.py.
The sample_data subfolder includes data that can be used when running the notebook.

The code was tested in Transkribus test environment.

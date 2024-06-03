EXSCLAIM2.0: LLM-powered Automatic **EX**traction, **S**eparation, and **C**aption-based natural **L**anguage **A**nnotation of **IM**ages from scientific figures


## 🤔 Consider Collaboration

If you find this tool or any of its derived capabilities useful, please consider registering as a user of Center for Nanoscale Materials. We will keep you posted of latest developments, as well as opportunities for computational resources, relevant data, and collaboration. Please contact Maria Chan (mchan@anl.gov) for details.

## Introduction to EXSCLAIM2.0

EXSCLAIM2.0 is a Python package combining EXSCLAIM! code with Large Language models (LLMs) that can be used for the automatic generation of datasets of labeled images from published papers. It in three main steps:
1. [JournalScraper]: scrap journal websites, acquiring figures, captions, and metadata
2. [HTMLScraper](https://github.com/MaterialEyes/exsclaim/wiki/JournalScraper): scrap user provided HTML files, acquiring figures, captions, and metadata 
3. [CaptionDistributor](https://github.com/MaterialEyes/exsclaim/wiki/JournalScraper): separate figure captions into the component chunks that refer to the figure's subfigures using LLMs and prompt engineering
4. [FigureSeparator](https://github.com/MaterialEyes/exsclaim/wiki/JournalScraper): separate figures into subfigures, detect scale information, label, and type of image

## Examples and tutorials
We provide several tutorials demonstrating how to use EXSCLAIM2.0:
1. [Nature_exsclaim_search](https://github.com/MaterialEyes/exsclaim2.0/blob/main/notebooks/1_Nature_exsclaim_search.ipynb): automatically scrapping data from literature and performing Named Entity Recognition (NER) on the extracted captions.
2. [HTMLScrapper](https://github.com/MaterialEyes/exsclaim2.0/blob/main/notebooks/2_HTMLScraper.ipynb): automatically scrapping data from user provided HTML files
3. [Microscopy_CLIP_retrieval](https://github.com/MaterialEyes/exsclaim2.0/blob/main/notebooks/3_Microscopy_CLIP_retrieval.ipynb): Using Microscopy_CLIP to perform image-to-image and text-to-image retrieval on our multimodal microscopy dataset.


## Using EXSCLAIM

### Requirements 
EXSCLAIM works with Python 3.6+. We recommend using a conda or python environment to install dependencies. To use the pipeline, you need a Query on which to run the pipeline. The query can be a JSON or Python dictionary (depending on how you are accessing the pipeline) and must have the parameters(/keys/attributes) defined in the [Query JSON schema](https://github.com/MaterialEyes/exsclaim/wiki/JSON-Schema#query-json-) and examples can be found [in the query directory](https://github.com/MaterialEyes/exsclaim/tree/master/query).

### Installation with Git
To install directly from github, run the following commands (it is recommended to run in a conda or python virtual environment):
```
git clone https://github.com/MaterialEyes/exsclaim.git
cd exsclaim
pip setup.py install
python load_models.py
```

#### Scrapping data from dynamic journal webpages
If scrapping data from Journals that use javascript (e.g. RSC, ACS) you need to setup chrome-driver and chrome and add their path to the `exsclaim/journal.py` file.
```
e.g. for a linux terminal you need the following:
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
wget https://chromedriver.storage.googleapis.com/90.0.4430.24/chromedriver_linux64.zip
```

If you run into errors, please check [Troubleshooting](https://github.com/MaterialEyes/exsclaim/wiki/Troubleshooting). If they persist, please open an issue.


## Acknowledgements <a name="credits"></a>
This material is based upon work supported by Laboratory Directed Research and Development (LDRD) funding from Argonne National Laboratory, provided by the Director, Office of Science, of the U.S. Department of Energy under Contract No. DE-AC02-06CH11357

This work was performed at the Center for Nanoscale Materials, a U.S. Department of Energy Office of Science User Facility, and supported by the U.S. Department of Energy, Office of Science, under Contract No. DE-AC02-06CH11357.

We gratefully acknowledge the computing resources provided on Bebop, a high-performance computing cluster operated by the Laboratory Computing Resource Center at Argonne National Laboratory.

## Citation
If you find EXSCLAIM! useful, please encourage its development by citing the following [paper](https://arxiv.org/abs/2103.10631) in your research:
```
Schwenker, E., Jiang, W. Spreadbury, T., Ferrier N., Cossairt, O., Chan M.K.Y., EXSCLAIM! - An automated pipeline for the construction and
labeling of materials imaging datasets from scientific literature. arXiv e-prints (2021): arXiv-2103
```

#### Bibtex
```
@article{schwenker2021exsclaim,
  title={EXSCLAIM! - An automated pipeline for the construction of labeled materials imaging datasets from literature},
  author={Schwenker, Eric and Jiang, Weixin and Spreadbury, Trevor and Ferrier, Nicola and Cossairt, Oliver and Chan, Maria KY},
  journal={arXiv e-prints},
  pages={arXiv--2103},
  year={2021}
}
```
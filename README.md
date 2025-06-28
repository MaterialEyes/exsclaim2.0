# EXSCLAIM2.0: LLM-powered Automatic **EX**traction, **S**eparation, and **C**aption-based natural **L**anguage **A**nnotation of **IM**ages from scientific figures
[![License](https://img.shields.io/github/license/MaterialEyes/exsclaim2.0.svg?color=blue)](https://github.com/MaterialEyes/exsclaim2.0/blob/main/LICENSE)
[![Website](https://img.shields.io/website?url=https%3A%2F%2Fexsclaim-dev.materialeyes.org%2F&up_message=online&down_message=offline&down_color=red&label=Website)
](https://exsclaim-dev.materialeyes.org)
[![Release](https://img.shields.io/github/release/MaterialEyes/exsclaim2.0.svg)](https://github.com/MaterialEyes/exsclaim2.0/releases)
[![DOI](https://zenodo.org/badge/DOI/10.48550/arXiv.2103.10631.svg)](https://arxiv.org/abs/2103.10631)

## 🤔 Consider Collaboration

If you find this tool or any of its derived capabilities useful, please consider registering as a user of Center for Nanoscale Materials. We will keep you posted of latest developments, as well as opportunities for computational resources, relevant data, and collaboration. Please contact Maria Chan (mchan@anl.gov) for details.

## Introduction to EXSCLAIM2.0

EXSCLAIM2.0 is a Python package combining EXSCLAIM! code with Large Language models (LLMs) that can be used for the automatic generation of datasets of labeled images from published papers.
There are four main steps:
1. [JournalScraper](https://github.com/MaterialEyes/exsclaim2.0/wiki/JournalScraper): scrap journal websites, acquiring figures, captions, and metadata
2. [CaptionDistributor](https://github.com/MaterialEyes/exsclaim2.0/wiki/CaptionDistributor): separate figure captions into the component chunks that refer to the figure's subfigures using LLMs and prompt engineering
3. [FigureSeparator](https://github.com/MaterialEyes/exsclaim2.0/wiki/FigureSeparator): separate figures into subfigures, detect scale information, label, and type of image

## Examples and tutorials
We provide several tutorials demonstrating how to use EXSCLAIM2.0:
1. [Nature_exsclaim_search](/notebooks/1_Nature_exsclaim_search.ipynb): automatically scrapping data from literature and performing Named Entity Recognition (NER) on the extracted captions.
2. [HTMLScraper](/notebooks/2_HTMLScraper.ipynb): automatically scrapping data from user provided HTML files
3. [Microscopy_CLIP_retrieval](/notebooks/3_Microscopy_CLIP_retrieval.ipynb): Using Microscopy_CLIP to perform image-to-image and text-to-image retrieval on our multimodal microscopy dataset.


## Installation
The guides to install EXSCLAIM through Pip, Git and Docker can be found within the [wiki](https://github.com/MaterialEyes/exsclaim2.0/wiki/Installation).
The guides include installing pre-compiled versions as well as building from the source code and then installing.

### Using Exsclaim 2.0
```python
from exsclaim import Pipeline
search_query = {
		...
}
results = Pipeline(search_query_json)
```
where `search_query` is either a dictionary representing a valid JSON object, or a Pathlike string pointing towards a valid JSON file,
or 
```shell
python -m exsclaim query {path to json file holding search query}
```
More extensive guides can be found within the [wiki](https://github.com/MaterialEyes/exsclaim2.0/wiki/Running-the-EXSCLAIM-Pipeline).

### Using Docker Compose
To use Docker Compose to host the service, run the following commands in the base directory:
```shell
docker compose build base
docker compose build {service(s) here}
docker compose up {service(s) here}
```

## Acknowledgements
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
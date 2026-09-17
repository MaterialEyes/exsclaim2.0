## EXSCLAIM Module

This directory contains the relevant code for the EXSCLAIM module, organized as follows:

 - [pipeline.py](./pipeline.py): Code for Pipeline class, which runs ExsclaimTool subclasses on Query JSONs.
 - [tool.py](./tool.py): Defines base ExsclaimTool class and CaptionDistributor, JournalScraper, and FigureSeparator subclasses. Each ExsclaimTool class is initialized with a Query JSON and has methods to run the tool, update the exsclaim.json, and load any necessary models.
 - [caption.py](./caption.py): Defines useful functions used by CaptionDistributor.
 - [journals/](./journals/): Defines the JournalFamily class. Nature and ACS subfamilies are defined and other journal families can be added and used by JournalScraper.
 - [figures/](./figures/): Additional modules for defining and training figure models.
 - [llms/](./llms/): Additional modules for defining and training caption models.
 - [utilities/](./utilities/): Modules with functions that are useful across several modules

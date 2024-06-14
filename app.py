from exsclaim import journal, pipeline, tool
from exsclaim.pipeline import Pipeline

test_pipeline = Pipeline('./query/nature-ESEM.json')
results = test_pipeline.run(caption_distributor=True,
                            journal_scraper=True,
                            figure_separator=True,
                            html_scraper=False
                            )

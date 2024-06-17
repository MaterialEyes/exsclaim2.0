from exsclaim.pipeline import Pipeline


def main():
    test_pipeline = Pipeline('./query/nature-ESEM.json')
    results = test_pipeline.run(caption_distributor=True,
                                journal_scraper=True,
                                figure_separator=True,
                                html_scraper=False
                                )
    print(f"{results=}")


if __name__ == "__main__":
    main()

from .models import *
from .serializers import *
from json import dumps
from exsclaim import Pipeline, get_database_connection_string
from os import getenv, system
from pathlib import Path
from psycopg import connect
from rest_framework import viewsets, mixins, response
from tarfile import open as tar_open


__all__ = ["ArticleViewSet", "FigureViewSet", "SubfigureViewSet", "ScaleBarViewSet", "ScaleBarLabelViewSet",
           "SubfigureLabelViewSet", "QueryViewSet"]


class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer


class FigureViewSet(viewsets.ModelViewSet):
    queryset = Figure.objects.all()
    serializer_class = FigureSerializer


class SubfigureViewSet(viewsets.ModelViewSet):
    queryset = Subfigure.objects.all()
    serializer_class = SubfigureSerializer


class ScaleBarViewSet(viewsets.ModelViewSet):
    queryset = ScaleBar.objects.all()
    serializer_class = ScaleBarSerializer


class ScaleBarLabelViewSet(viewsets.ModelViewSet):
    queryset = ScaleBarLabel.objects.all()
    serializer_class = ScaleBarLabelSerializer


class SubfigureLabelViewSet(viewsets.ModelViewSet):
    queryset = SubfigureLabel.objects.all()
    serializer_class = SubfigureLabelSerializer


class QueryViewSet(viewsets.ModelViewSet):
    queryset = Query.objects.all()
    serializer_class = QuerySerializer

    # deleting test data
    # queryset.delete()

    # receives input query data from UI and posts it to API
    def create(self, request, *args, **kwargs):
        if not self.request.session.exists(self.request.session.session_key):
            self.request.session.create()

        input_query = request.data

        name = input_query.get('name')
        journal_family = input_query.get('journal_family').lower()
        maximum_scraped = int(input_query.get('maximum_scraped'))
        sortby = input_query.get('sortby')
        term = input_query.get('term')
        synonyms = input_query.get('synonyms')
        save_format = input_query.get('save_format')
        access = input_query.get('access', False)
        llm = input_query.get('llm')
        model_key = input_query.get('model_key')

        # running user input through EXSCLAIM
        # follow this: https://github.com/MaterialEyes/exsclaim-ui/blob/main/query/views.py

        with connect(get_database_connection_string()) as db:
            cursor = db.cursor()
            cursor.execute("SELECT uuid_generate_v4() AS uuid;")
            uuid = str(cursor.fetchone()[0])

            results_dir = Path("/results") / uuid
            results_dir.mkdir(exist_ok=True, parents=True)

            exsclaim_input = {
                "name": name,
                "journal_family": journal_family,
                "maximum_scraped": maximum_scraped,
                "sortby": sortby,
                "query": {
                    "search_field_1": {
                        "term": term,
                        "synonyms": synonyms
                    }
                },
                "llm": llm,
                "openai_API": model_key,
                "open": access,
                "save_format": save_format,
                "logging": ["print", "exsclaim.log"],
                "results_dir": str(results_dir)
            }

            try:
                test_pipeline = Pipeline(exsclaim_input)
                results = test_pipeline.run()
            except NameError as e:
                raise e

            print(results)

        queryset = Query.objects.all()

        # if there is a query that exists already, replace it with the new query
        if queryset.exists():
            input_query = queryset.first()
            input_query.name = name
            input_query.journal_family = journal_family
            input_query.maximum_scraped = maximum_scraped
            input_query.sortby = sortby
            input_query.term = term
            input_query.synonyms = synonyms
            input_query.save_format = save_format
            input_query.access = access
            input_query.llm = llm
            input_query.llm_token = model_key
            input_query.save(update_fields=['name', 'journal_family', 'maximum_scraped', 'sortby', 'term', 'synonyms', 'save_format', 'access', 'llm', 'model_key'])

            serializer = QuerySerializer(input_query)

            return response.Response(serializer.data)

        # make a new query and store it
        input_query = Query.objects.create(name=name, journal_family=journal_family, maximum_scraped=maximum_scraped, sortby=sortby, term=term, synonyms=synonyms, save_format=save_format, access=access, llm=llm, model_key=model_key)
        input_query.save()

        serializer = QuerySerializer(input_query)

        return response.Response(serializer.data)

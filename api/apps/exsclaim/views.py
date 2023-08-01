from rest_framework import viewsets, mixins, views, response, generics, status
#import exsclaim

from .models import (
    Article,
    Figure,
    Subfigure,
    ScaleBar,
    ScaleBarLabel,
    SubfigureLabel,
    Query,
)
from .serializers import (
    ArticleSerializer,
    FigureSerializer,
    SubfigureSerializer,
    ScaleBarSerializer,
    ScaleBarLabelSerializer,
    SubfigureLabelSerializer,
    QuerySerializer,
)


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

# watch this: https://www.youtube.com/watch?v=H9rHrlNTpq8&ab_channel=TechWithTim

class QueryViewSet(viewsets.ModelViewSet):
    queryset = Query.objects.all()
    serializer_class = QuerySerializer

    # deleting test data
    #queryset.delete()

    def create(self, request, *args, **kwargs):
        if not self.request.session.exists(self.request.session.session_key):
            self.request.session.create()

        input_query = request.data

        name = input_query.get('name')
        journal_family = input_query.get('journal_family')
        maximum_scraped = input_query.get('maximum_scraped')
        sortby = input_query.get('sortby')
        term = input_query.get('term')
        synonyms = input_query.get('synonyms')
        save_format = input_query.get('save_format')
        open = input_query.get('open')

        queryset = Query.objects.all()

        if queryset.exists():
            input_query = queryset.first()
            input_query.name = name
            input_query.journal_family = journal_family
            input_query.maximum_scraped = maximum_scraped
            input_query.sortby = sortby
            input_query.term = term
            input_query.synonyms = synonyms
            input_query.save_format = save_format
            input_query.open = open
            input_query.save(update_fields=['name', 'journal_family', 'maximum_scraped', 'sortby', 'term', 'synonyms', 'save_format', 'open'])

            serializer = QuerySerializer(input_query)

            return response.Response(serializer.data)

        else:
            input_query = Query.objects.create(name=name, journal_family=journal_family, maximum_scraped=maximum_scraped, sortby=sortby, term=term, synonyms=synonyms, save_format=save_format, open=open)
            input_query.save()

            serializer = QuerySerializer(input_query)

            return response.Response(serializer.data)

    '''

    def create(self, request, *args, **kwargs):
        if not self.request.session.exists(self.request.session.session_key):
            self.request.session.create()

        queryset = Query.objects.all()
        serializer = self.serializer_class(data = request.data)

        if serializer.is_valid():
            name = serializer.data.get('name')
            journal_family = serializer.data.get('journal_family')
            maximum_scraped = serializer.data.get('maximum_scraped')
            sortby = serializer.data.get('sortby')
            term = serializer.data.get('term')
            synonyms = serializer.data.get('synonyms')
            save_format = serializer.data.get('save_format')
            open = serializer.data.get('open')

            if queryset.exists():
                input_query = queryset[0]
                input_query.name = name
                input_query.journal_family = journal_family
                input_query.maximum_scraped = maximum_scraped
                input_query.sortby = sortby
                input_query.term = term
                input_query.synonyms = synonyms
                input_query.save_format = save_format
                input_query.open = open
                input_query.save(update_fields=['name', 'journal_family', 'maximum_scraped', 'sortby', 'term', 'synonyms', 'save_format', 'open'])
                
            else:
                input_query = Query(name=name, journal_family=journal_family, maximum_scraped=maximum_scraped, sortby=sortby, term=term, synonyms=synonyms, save_format=save_format, open=open)
                input_query.save()

        return response.Response(status=200)

        '''

from rest_framework import viewsets, mixins
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

    def post(self, request, format=None):
        serializer = self.serializer_class(data = request.data)

        name = serializer.data.name
        journal_family = serializer.data.journal_family
        maximum_scraped = serializer.data.maximum_scraped
        sortby = serializer.data.sortby
        query = serializer.data.query
        save_format = serializer.save_format
        open = serializer.open

        query = Query(name=name, journal_family=journal_family, maximum_scraped=maximum_scraped, sortby=sortby, query=query, save_format=save_format, open=open)
        query.save()

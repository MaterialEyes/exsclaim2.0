from rest_framework import viewsets, mixins

from .models import (
    Article,
    Figure,
    Subfigure,
    ScaleBar,
    ScaleBarLabel,
    SubfigureLabel,
)
from .serializers import (
    ArticleSerializer,
    FigureSerializer,
    SubfigureSerializer,
    ScaleBarSerializer,
    ScaleBarLabelSerializer,
    SubfigureLabelSerializer,
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

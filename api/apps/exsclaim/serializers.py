from rest_framework import serializers
from .models import (
    Article,
    Figure,
    Subfigure,
    ScaleBar,
    ScaleBarLabel,
    SubfigureLabel
)


class ArticleSerializer(serializers.ModelSerializer):

    class Meta:
        model = Article
        fields = "__all__"

class FigureSerializer(serializers.ModelSerializer):
    article = serializers.PrimaryKeyRelatedField(queryset=Article.objects.all())

    class Meta:
        model = Figure
        fields = "__all__"

class SubfigureSerializer(serializers.ModelSerializer):
    figure = serializers.PrimaryKeyRelatedField(queryset=Figure.objects.all())

    class Meta:
        model = Subfigure
        fields = "__all__"

class ScaleBarSerializer(serializers.ModelSerializer):
    subfigure = serializers.PrimaryKeyRelatedField(queryset=Subfigure.objects.all())

    class Meta:
        model = ScaleBar
        fields = "__all__"

class ScaleBarLabelSerializer(serializers.ModelSerializer):
    scale_bar = serializers.PrimaryKeyRelatedField(queryset=ScaleBar.objects.all())

    class Meta:
        model = ScaleBarLabel
        fields = "__all__"

class SubfigureLabelSerializer(serializers.ModelSerializer):
    subfigure = serializers.PrimaryKeyRelatedField(queryset=Subfigure.objects.all())
    
    class Meta:
        model = SubfigureLabel
        fields = "__all__"

from django.db import models
from django.contrib.postgres.fields import ArrayField
from pathlib import Path


__all__ = ["Article", "Figure", "Subfigure", "ScaleBar", "ScaleBarLabel", "SubfigureLabel", "Query"]


def get_figures_path():
    current_dir = Path(__file__).resolve(strict=True).parent
    figures = current_dir.parent.parent
    return str(figures)


class Article(models.Model):
    doi = models.CharField(primary_key=True, max_length=32, unique=True, default="unknown")
    title = models.TextField()
    url = models.URLField()
    license = models.URLField(null=True, blank=True)
    open = models.BooleanField(null=False, blank=True)
    authors = models.CharField(max_length=250, null=True)
    abstract = models.TextField(null=True, blank=True)


class Figure(models.Model):
    # Figure ID "<doi>-fig<figure number>"
    figure_id = models.CharField(primary_key=True, max_length=40, unique=True, default="unknown")
    caption = models.TextField(null=True, blank=True)
    caption_delimiter = models.CharField(max_length=12, null=True, blank=True)
    url = models.URLField()
    path = models.FilePathField(path=get_figures_path())
    article = models.ForeignKey(
        'Article',
        on_delete=models.CASCADE
    )


class Subfigure(models.Model):
    # Subfigure ID is article "<doi>-fig<figure number>-<subfigure label>"
    subfigure_id = models.CharField(primary_key=True, max_length=44, unique=True, default="unknown")
    figure = models.ForeignKey(
        'Figure',
        on_delete=models.CASCADE
    )
    MICROSCOPY = "MC"
    DIFFRACTION = "DF"
    GRAPH = "GR"
    PHOTO = "PH"
    ILLUSTRATION = "IL"
    UNCLEAR = "UN"
    PARENT = "PT"
    CLASSIFICATION_CHOICES = [
        (MICROSCOPY, "microscopy"),
        (DIFFRACTION, "diffraction"),
        (GRAPH, "graph"),
        (PHOTO, "basic_photo"),
        (ILLUSTRATION, "illustration"),
        (UNCLEAR, "unclear"),
        (PARENT, "parent")
    ]
    classification = models.CharField(
        max_length=2,
        choices=CLASSIFICATION_CHOICES
    )
    height = models.FloatField()
    width = models.FloatField()
    nm_height = models.FloatField(null=True, blank=True)
    nm_width = models.FloatField(null=True, blank=True)
    x1 = models.IntegerField(null=True)
    y1 = models.IntegerField(null=True)
    x2 = models.IntegerField(null=True)
    y2 = models.IntegerField(null=True)
    caption = models.TextField(blank=True, null=True)
    keywords = ArrayField(
        models.CharField(max_length=20),
        null=True, blank=True
    )
    general = ArrayField(
        models.CharField(max_length=20),
        null=True, blank=True
    )


class ScaleBar(models.Model):
    # ScaleBar ID is "<article doi>-fig<figure number>-<subfigure label>-<scale bar #>"
    scale_bar_id = models.CharField(
        primary_key=True,
        unique=True,
        max_length=48,
        default="unknown"
    )
    x1 = models.IntegerField(null=True)
    y1 = models.IntegerField(null=True)
    x2 = models.IntegerField(null=True)
    y2 = models.IntegerField(null=True)
    length = models.CharField(max_length=8, null=True, blank=True)
    line_label_distance = models.IntegerField(null=True, blank=True)
    confidence = models.FloatField(null=True, blank=True)
    subfigure = models.ForeignKey(
        'Subfigure',
        on_delete=models.CASCADE,
        null=True
    )


class ScaleBarLabel(models.Model):
    text = models.CharField(max_length=15)
    x1 = models.IntegerField(null=True)
    y1 = models.IntegerField(null=True)
    x2 = models.IntegerField(null=True)
    y2 = models.IntegerField(null=True)
    label_confidence = models.FloatField(null=True, blank=True)
    box_confidence = models.FloatField(null=True, blank=True)
    nm = models.FloatField(null=True, blank=True)
    scale_bar = models.ForeignKey('ScaleBar', on_delete=models.CASCADE, null=True)


class SubfigureLabel(models.Model):
    text = models.CharField(max_length=15)
    x1 = models.IntegerField(null=True)
    y1 = models.IntegerField(null=True)
    x2 = models.IntegerField(null=True)
    y2 = models.IntegerField(null=True)
    label_confidence = models.FloatField(null=True, blank=True)
    box_confidence = models.FloatField(null=True, blank=True)
    subfigure = models.ForeignKey('Subfigure', on_delete=models.CASCADE, null=True)  


class Query(models.Model):
    id = models.AutoField(primary_key=True) # auto-create id for query
    name = models.TextField(null=True)
    NATURE = "Nature"
    RCS = "RCS"
    JOURNAL_CHOICES = [
        (NATURE, "Nature"),
        (RCS, "RCS")
    ]
    journal_family = models.CharField(
        max_length=10,
        choices=JOURNAL_CHOICES
    )
    maximum_scraped = models.IntegerField(null=True)
    RELEVANT = "relevant"
    RECENT = "recent"
    SORT_CHOICES = [
        (RELEVANT, "relevant"),
        (RECENT, "recent")
    ]
    sortby = models.CharField(
        max_length=10,
        choices=SORT_CHOICES
    )
    term = models.TextField(null=True)
    synonyms = ArrayField(
        models.CharField(max_length=30),
        null=True, blank=True
    )
    MONGO = "mongo"
    CSV = "csv"
    POSTGRES = "postgres"
    VISUALIZE = "visualize"
    BOXES = "boxes"
    SUBFIGURES = "save_subfigures"
    FORMAT_CHOICES = [
        (MONGO, "mongo"),
        (CSV, "csv"),
        (POSTGRES, "postgres"),
        (VISUALIZE, "visualize"),
        (BOXES, "boxes"),
        (SUBFIGURES, "save_subfigures")
    ]
    save_format = models.CharField(
        max_length=20,
        choices=FORMAT_CHOICES,
        default="postgres"
    )
    access = models.BooleanField(null=True, blank=True)
    VICUNA = "vicuna"
    GPT3 = "gpt3.5-turbo"
    GPT4 = "gpt-4"
    MODEL_CHOICES = [
        (VICUNA, "vicuna"),
        (GPT3, "gpt3.5-turbo"),
        (GPT4, "gpt-4")
    ]
    llm = models.CharField(
        max_length=15,
        choices=MODEL_CHOICES,
        default=POSTGRES
    )
    model_key = models.TextField(null=True)

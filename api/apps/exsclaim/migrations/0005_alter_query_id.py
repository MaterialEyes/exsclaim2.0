# Generated by Django 4.0 on 2023-07-31 19:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exsclaim', '0004_remove_query_query_query_synonyms_query_term_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='query',
            name='id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
    ]

# Generated by Django 4.0 on 2023-08-01 19:51

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exsclaim', '0005_alter_query_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='query',
            name='logging',
        ),
        migrations.RemoveField(
            model_name='query',
            name='mongo_connection',
        ),
        migrations.RemoveField(
            model_name='query',
            name='results_dir',
        ),
    ]

# Generated by Django 3.0.9 on 2020-09-02 11:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('change', '0036_auto_20200902_1052'),
    ]

    operations = [
        migrations.AddField(
            model_name='provisionset',
            name='odin_output',
            field=models.TextField(blank=True, null=True),
        ),
    ]
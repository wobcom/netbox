# Generated by Django 2.1.4 on 2019-04-29 07:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('configuration', '0018_routemap'),
    ]

    operations = [
        migrations.AddField(
            model_name='routemap',
            name='neighbors',
            field=models.ManyToManyField(blank=True, null=True, to='configuration.BGPNeighbor'),
        ),
    ]

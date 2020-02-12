# Generated by Django 2.1.4 on 2019-04-30 09:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('configuration', '0020_auto_20190430_0958'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bgpsession',
            name='communities',
            field=models.ManyToManyField(blank=True, related_name='sessions', to='configuration.BGPCommunity'),
        ),
        migrations.AlterField(
            model_name='routemap',
            name='neighbors',
            field=models.ManyToManyField(blank=True, to='configuration.BGPNeighbor'),
        ),
    ]

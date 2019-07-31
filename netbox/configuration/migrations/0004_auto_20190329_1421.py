# Generated by Django 2.1.4 on 2019-03-29 14:21

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import ipam.fields


class Migration(migrations.Migration):

    dependencies = [
        ('dcim', '0076_interface_overlay_network'),
        ('configuration', '0003_bgpconfiguration_description'),
    ]

    operations = [
        migrations.CreateModel(
            name='BGPCommunity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('community', models.PositiveIntegerField()),
                ('name', models.CharField(max_length=128)),
                ('description', models.TextField(blank=True, max_length=255, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='BGPSession',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('neighbor', ipam.fields.IPAddressField()),
                ('remote_as', models.PositiveIntegerField(validators=[django.core.validators.MaxValueValidator(65536)])),
                ('description', models.TextField(blank=True, max_length=255, null=True)),
                ('devices', models.ManyToManyField(to='dcim.Device')),
                ('session', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='configuration.BGPCommunity')),
            ],
            options={
                'verbose_name': 'BGP Session',
            },
        ),
        migrations.RemoveField(
            model_name='bgpconfiguration',
            name='devices',
        ),
        migrations.DeleteModel(
            name='BGPConfiguration',
        ),
    ]

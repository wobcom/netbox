# Generated by Django 3.1 on 2020-12-09 11:44

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dcim', '0117_merge_20201209_1144'),
    ]

    operations = [
        migrations.DeleteModel(
            name='DeviceLicense',
        ),
    ]
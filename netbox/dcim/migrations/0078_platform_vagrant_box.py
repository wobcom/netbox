# Generated by Django 2.1.4 on 2019-07-09 13:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dcim', '0077_devicelicense'),
    ]

    operations = [
        migrations.AddField(
            model_name='platform',
            name='vagrant_box',
            field=models.CharField(max_length=50, null=True),
        ),
    ]

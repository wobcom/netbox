# Generated by Django 2.1.4 on 2019-05-08 12:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('configuration', '0025_auto_20190508_1019'),
    ]

    operations = [
        migrations.AddField(
            model_name='bgpasn',
            name='redistribute_connected',
            field=models.BooleanField(default=False),
        ),
    ]
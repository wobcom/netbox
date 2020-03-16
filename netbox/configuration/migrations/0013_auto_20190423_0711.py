# Generated by Django 2.1.4 on 2019-04-23 07:11

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('configuration', '0012_auto_20190423_0710'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bgpsession',
            name='device_b_as',
            field=models.PositiveIntegerField(blank=True, null=True, validators=[django.core.validators.MaxValueValidator(4294967296)]),
        ),
    ]
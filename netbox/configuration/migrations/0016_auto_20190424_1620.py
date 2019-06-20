# Generated by Django 2.1.4 on 2019-04-24 16:20

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('configuration', '0015_auto_20190424_1025'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bgpsession',
            name='interface_a_as',
            field=models.BigIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(4294967296)]),
        ),
        migrations.AlterField(
            model_name='bgpsession',
            name='interface_b_as',
            field=models.BigIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(4294967296)]),
        ),
        migrations.AlterField(
            model_name='bgpsession',
            name='remote_as',
            field=models.BigIntegerField(blank=True, null=True, validators=[django.core.validators.MaxValueValidator(4294967294)]),
        ),
    ]

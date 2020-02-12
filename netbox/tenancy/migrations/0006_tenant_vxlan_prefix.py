# Generated by Django 2.1.4 on 2019-01-22 07:47

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenancy', '0005_change_logging'),
    ]

    operations = [
        migrations.AddField(
            model_name='tenant',
            name='vxlan_prefix',
            field=models.PositiveSmallIntegerField(default=1, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(4094)]),
            preserve_default=False,
        ),
    ]

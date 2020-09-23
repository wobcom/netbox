# Generated by Django 2.1.4 on 2019-01-25 10:12

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenancy', '0006_tenant_vxlan_prefix'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tenant',
            name='vxlan_prefix',
            field=models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(16777215)]),
        ),
    ]
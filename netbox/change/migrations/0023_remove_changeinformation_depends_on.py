# Generated by Django 2.2.6 on 2020-01-24 09:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('change', '0022_auto_20200124_0858'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='changeinformation',
            name='depends_on',
        ),
    ]

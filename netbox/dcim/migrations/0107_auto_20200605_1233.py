# Generated by Django 3.0.5 on 2020-06-05 12:33

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('virtualization', '0016_remove_virtualmachine_platform_version'),
        ('dcim', '0106_flatten_platform_versions'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='device',
            name='platform_version',
        ),
        migrations.DeleteModel(
            name='PlatformVersion',
        ),
    ]

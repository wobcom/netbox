# Generated by Django 3.0.8 on 2020-08-13 09:14

from django.db import migrations, models


def status_translation(apps, schema_editor):
    ProvisionSet = apps.get_model('change', 'ProvisionSet')

    lookup = {
        '0': 'not_started',
        '1': 'running',
        '2': 'finished',
        '3': 'failed',
        '4': 'aborted',
        '5': 'reviewing',
    }

    for p in ProvisionSet.objects.all():
        p.status = lookup[p.status]
        p.save()


class Migration(migrations.Migration):

    dependencies = [
        ('change', '0032_auto_20200303_0823'),
    ]

    operations = [
        migrations.AlterField(
            model_name='provisionset',
            name='status',
            field=models.CharField(default='not_started', max_length=20),
        ),
        migrations.RunPython(status_translation)
    ]
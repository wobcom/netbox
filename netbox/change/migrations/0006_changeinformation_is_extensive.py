# Generated by Django 2.0.9 on 2018-12-04 15:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('change', '0005_changeset_started'),
    ]

    operations = [
        migrations.AddField(
            model_name='changeinformation',
            name='is_extensive',
            field=models.BooleanField(default=False, verbose_name='Is an extensive change'),
            preserve_default=False,
        ),
    ]
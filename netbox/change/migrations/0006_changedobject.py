# Generated by Django 2.0.9 on 2018-10-31 12:59

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('change', '0005_auto_20181021_1326'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChangedObject',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('time', models.DateTimeField(auto_now_add=True)),
                ('changed_object_id', models.PositiveIntegerField()),
                ('changed_object_type', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='+', to='contenttypes.ContentType')),
                ('changeset', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='change.ChangeSet')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]

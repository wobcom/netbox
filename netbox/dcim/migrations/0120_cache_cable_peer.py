import sys

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('dcim', '0119_inventoryitem_mptt_rebuild'),
    ]

    operations = [
        migrations.AddField(
            model_name='consoleport',
            name='_cable_peer_id',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='consoleport',
            name='_cable_peer_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='contenttypes.contenttype'),
        ),
        migrations.AddField(
            model_name='consoleserverport',
            name='_cable_peer_id',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='consoleserverport',
            name='_cable_peer_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='contenttypes.contenttype'),
        ),
        migrations.AddField(
            model_name='frontport',
            name='_cable_peer_id',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='frontport',
            name='_cable_peer_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='contenttypes.contenttype'),
        ),
        migrations.AddField(
            model_name='interface',
            name='_cable_peer_id',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='interface',
            name='_cable_peer_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='contenttypes.contenttype'),
        ),
        migrations.AddField(
            model_name='powerfeed',
            name='_cable_peer_id',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='powerfeed',
            name='_cable_peer_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='contenttypes.contenttype'),
        ),
        migrations.AddField(
            model_name='poweroutlet',
            name='_cable_peer_id',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='poweroutlet',
            name='_cable_peer_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='contenttypes.contenttype'),
        ),
        migrations.AddField(
            model_name='powerport',
            name='_cable_peer_id',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='powerport',
            name='_cable_peer_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='contenttypes.contenttype'),
        ),
        migrations.AddField(
            model_name='rearport',
            name='_cable_peer_id',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='rearport',
            name='_cable_peer_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='contenttypes.contenttype'),
        ),
    ]

# Generated by Django 2.1.4 on 2019-02-14 13:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dcim', '0075_remove_interface_vxlan'),
        ('ipam', '0027_auto_20190214_1346'),
    ]

    operations = [
        migrations.AddField(
            model_name='interface',
            name='overlay_network',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='interfaces', to='ipam.OverlayNetwork'),
        ),
    ]

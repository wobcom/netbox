# Generated by Django 2.1.4 on 2019-02-06 15:42

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dcim', '0071_auto_20190206_1518'),
    ]

    operations = [
        migrations.AlterField(
            model_name='interface',
            name='vxlan',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='interfaces', to='ipam.VxLAN'),
        ),
    ]

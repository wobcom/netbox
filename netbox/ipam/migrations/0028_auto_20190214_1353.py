# Generated by Django 2.1.4 on 2019-02-14 13:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ipam', '0027_auto_20190214_1346'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='overlaynetwork',
            options={'ordering': ['site', 'group', 'vxlan_prefix'], 'verbose_name': 'Overlay Network', 'verbose_name_plural': 'Overlay Networks'},
        ),
        migrations.AlterModelOptions(
            name='overlaynetworkgroup',
            options={'ordering': ['site', 'name'], 'verbose_name': 'Overlay Network group', 'verbose_name_plural': 'Overlay Network groups'},
        ),
        migrations.RenameField(
            model_name='overlaynetwork',
            old_name='vni',
            new_name='vxlan_prefix',
        ),
        migrations.AlterUniqueTogether(
            name='overlaynetwork',
            unique_together={('group', 'vxlan_prefix'), ('group', 'name')},
        ),
    ]
# Generated by Django 2.1.4 on 2019-02-13 15:49

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dcim', '0073_auto_20190211_1613'),
    ]

    operations = [
        migrations.AlterField(
            model_name='interface',
            name='vxlan',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='interfaces', to='ipam.VxLAN'),
        ),
    ]
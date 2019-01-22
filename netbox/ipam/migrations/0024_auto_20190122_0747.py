# Generated by Django 2.1.4 on 2019-01-22 07:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ipam', '0023_change_logging'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vlan',
            name='tenant',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.PROTECT, related_name='vlans', to='tenancy.Tenant'),
            preserve_default=False,
        ),
    ]

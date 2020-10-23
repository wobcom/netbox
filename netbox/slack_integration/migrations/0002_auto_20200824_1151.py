# Generated by Django 3.0.9 on 2020-08-24 11:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('slack_integration', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='slackmessage',
            name='object_types',
            field=models.ManyToManyField(limit_choices_to={'model__in': ['permission', 'group_permissions', 'group', 'user_groups', 'user_user_permissions', 'user', 'changeset', 'provisionset', 'webhook', 'customfield', 'region', 'site', 'rackgroup', 'rackrole', 'rack', 'rackreservation', 'manufacturer', 'devicetype', 'devicerole', 'platform', 'platformversion', 'device', 'devicelicense', 'consoleport', 'consoleserverport', 'powerport', 'poweroutlet', 'interface', 'frontport', 'rearport', 'devicebay', 'inventoryitem', 'virtualchassis', 'cable', 'powerpanel', 'powerfeed', 'tenantgroup', 'tenant', 'vrf_imports', 'vrf', 'rir', 'aggregate', 'role', 'prefix', 'ipaddress', 'overlaynetworkgroup', 'vlangroup', 'overlaynetwork', 'vlan', 'service_ipaddresses', 'service', 'clustertype', 'clustergroup', 'cluster', 'virtualmachine', 'provider', 'circuittype', 'circuit', 'circuittermination']}, related_name='slack_messages', to='contenttypes.ContentType'),
        ),
    ]
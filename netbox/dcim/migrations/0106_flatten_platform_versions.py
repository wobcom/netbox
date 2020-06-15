from django.db import migrations
from django.utils.text import slugify


def flatten_platforms(apps, schema_editor):
    Platform = apps.get_model('dcim', 'Platform')
    PlatformVersion = apps.get_model('dcim', 'PlatformVersion')
    Device = apps.get_model('dcim', 'Device')
    VirtualMachine = apps.get_model('virtualization', 'VirtualMachine')

    db_alias = schema_editor.connection.alias

    for pv in PlatformVersion.objects.using(db_alias).all():
        new_platform_name = "{} {}".format(pv.platform.name, pv.name)
        if not Platform.objects.using(db_alias).filter(name=new_platform_name).exists():
            pv.platform.pk = None
            pv.platform.name = new_platform_name
            pv.platform.slug = slugify(new_platform_name)
            pv.platform.save()
        subst_platform = Platform.objects.using(db_alias).get(name=new_platform_name)
        Device.objects.using(db_alias).filter(platform_version=pv).update(platform=subst_platform)
        VirtualMachine.objects.using(db_alias).filter(platform_version=pv).update(platform=subst_platform)


class Migration(migrations.Migration):

    dependencies = [
        ('dcim', '0105_merge_20200416_0718'),
    ]

    operations = [
        migrations.RunPython(flatten_platforms),
    ]

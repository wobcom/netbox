from django.core.management.base import BaseCommand, CommandError
from change.models import ChangeSet
from dcim.models import Device

class Command(BaseCommand):
    help = 'Exports device configurations (host_vars) to the filesystem'

    def __init__(self):
        self.change_set = ChangeSet()

    def add_arguments(self, parser):
        parser.add_argument('--dest', required=False, type=str, default='/tmp')
        parser.add_argument('--devices', nargs='*', required=False, type=str)

    def handle(self, *args, **options):
        if options['devices']:
            for device_name in options['devices']:
                try:
                    device = Device.objects.get(name=device_name)
                except:
                    print(f"Error retrieving {device_name}! Skipping ...")
                    continue
                self.export_device_to_disk(device, f"{options['dest']}/{device.name}.yml")
        else:
            for device in Device.objects.all():
                self.export_device_to_disk(device, f"{options['dest']}/{device.name}.yml") 

    def export_device_to_disk(self, device, dest_file):
        yaml = self.change_set.yamlify_device(device)
        try:
            with open(dest_file, 'w+') as file_handle:
                file_handle.write(yaml)
        except:
            print(f"Error writing to {dest_file}! Maybe check permissions? Skipping ...")

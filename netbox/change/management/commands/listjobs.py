from django.core.management.base import BaseCommand
from netbox.settings import configuration


class Command(BaseCommand):
    help = "list all configured pipeline jobs"

    def handle(self, *args, **options):
        print("First stage:")
        for index, job in enumerate(configuration.PROVISIONING_STAGE_1):
            print("    {:>2}: {}".format(index, " ".join(job['command'])))
        print()
        print("Second stage:")
        for index, job in enumerate(configuration.PROVISIONING_STAGE_2):
            print("    {:>2}: {}".format(index + len(configuration.PROVISIONING_STAGE_1), " ".join(job['command'])))

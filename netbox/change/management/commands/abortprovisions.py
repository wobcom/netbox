from django.core.management.base import BaseCommand
from change.models import ProvisionSet

class Command(BaseCommand):
    help = 'Marks all running provisions as aborted.'

    def handle(self, *args, **options):
        updated = ProvisionSet.objects.filter(status=ProvisionSet.RUNNING)\
                                      .update(status=ProvisionSet.ABORTED)

        print('Marked {} provisions as aborted.'.format(updated))

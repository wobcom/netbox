from . import JobBaseCommand
from sys import argv


class Command(JobBaseCommand):
    def handle_job(self, index, job):
        print("# Please use the command in this way:")
        print("#    source <(netbox-manage loadjobenv {})".format(index))
        environment = job.get('environment', {})

        for key, value in environment.items():
            print("export {}='{}'".format(key, value))

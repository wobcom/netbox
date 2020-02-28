from django.core.management.base import BaseCommand, CommandError
from netbox.settings import configuration


class JobBaseCommand(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('job_id',
                            type=int,
                            help="ID of the job to view from `listjobs` command",
        )

    def handle(self, *args, **options):
        job_id = options['job_id']
        if job_id < len(configuration.PROVISIONING_STAGE_1):
            self.handle_job(job_id, configuration.PROVISIONING_STAGE_1[job_id])
        elif job_id < (len(configuration.PROVISIONING_STAGE_1) + len(configuration.PROVISIONING_STAGE_2)):
            self.handle_job(job_id,
                            configuration.PROVISIONING_STAGE_2[job_id - len(configuration.PROVISIONING_STAGE_1)],
            )
        else:
            raise CommandError("Job with id `{}` does not exist.".format(job_id))

    def handle_job(self, index, job):
        pass

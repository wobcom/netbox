from . import JobBaseCommand


class Command(JobBaseCommand):

    def handle_job(self, index, job):
        print("Job #{}:".format(index))
        print("    Command: {}".format(" ".join(job['command'])))
        environment = job.get('environment', {})
        if len(environment) > 0:
            longest_key = 0
            for key, value in environment.items():
                longest_key = len(key) if len(key) > longest_key else longest_key
            print("    Environment:")
            for key, value in environment.items():
                print(("        {:<" + str(longest_key) + "} : {}").format(key, value))

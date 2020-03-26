from django.dispatch import Signal

provision_finished = Signal(providing_args=['provision_set'])

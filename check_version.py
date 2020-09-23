from django.conf import settings
from os import environ

target = environ.get('CI_COMMIT_REF_NAME')

if target != settings.VERSION:
    print(f'Version in NetBox settings ({settings.VERSION}) and tag name ({target}) does not match')
    exit(1)

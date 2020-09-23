from netbox.netbox.version import VERSION
from os import environ

target = environ.get('CI_COMMIT_REF_NAME')

if target != VERSION:
    print(f'Version in NetBox settings ({VERSION}) and tag name ({target}) does not match')
    exit(1)

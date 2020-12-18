###################################################################
#  This file serves as a base configuration for testing purposes  #
#  only. It is not intended for production use.                   #
###################################################################

ALLOWED_HOSTS = ['*']

DATABASE = {
    'NAME': 'netbox',
    'USER': '',
    'PASSWORD': '',
    'HOST': 'postgres',
    'PORT': '',
    'CONN_MAX_AGE': 300,
}

PLUGINS = [
    'extras.tests.dummy_plugin',
]

REDIS = {
    'tasks': {
        'HOST': 'redis',
        'PORT': 6379,
        'PASSWORD': '',
        'DATABASE': 0,
        'SSL': False,
    },
    'caching': {
        'HOST': 'redis',
        'PORT': 6379,
        'PASSWORD': '',
        'DATABASE': 1,
        'SSL': False,
    }
}

SECRET_KEY = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'

ODIN_WORKER_URL = 'http://localhost:8001'

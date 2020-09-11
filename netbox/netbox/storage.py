from django.contrib.staticfiles.storage import StaticFilesStorage
from django.conf import settings


class VersionedStaticFilesStorage(StaticFilesStorage):
    def url(self, name):
        url = super(VersionedStaticFilesStorage, self).url(name)
        return f"{url}?v={settings.VERSION}"

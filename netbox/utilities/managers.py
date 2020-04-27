from django.db.models import Manager
from django.db.models.signals import pre_save, post_save


class BaseManager(Manager):
    def bulk_create(self, objs, **kwargs):
        objs = list(objs)
        for i in objs:
            pre_save.send(i.__class__, instance=i, created=True, using=None)
        a = super().bulk_create(objs, **kwargs)
        for i in objs:
            post_save.send(i.__class__, instance=i, created=True, using=None)
        return a

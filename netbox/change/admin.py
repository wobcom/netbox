from django.contrib import admin

from netbox.admin import admin_site

from .models import ChangeSet

@admin.register(ChangeSet, site=admin_site)
class ChangeSetAdmin(admin.ModelAdmin):
    list_display = ('started', 'user', 'active')

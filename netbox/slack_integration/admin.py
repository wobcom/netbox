from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from django import forms

from netbox.admin import admin_site

from extras.admin import order_content_types

from .models import SlackChannel, SlackMessage


@admin.register(SlackChannel, site=admin_site)
class SlackChannelAdmin(admin.ModelAdmin):
    list_display = ('name',)


class SlackMessageForm(forms.ModelForm):
    class Meta:
        model = SlackMessage
        exclude = []
        widgets = {
            'object_types': FilteredSelectMultiple(
                verbose_name='Object types',
                is_stacked=False,
            )
        }

    def __init__(self, *args, **kwargs):
        super(SlackMessageForm, self).__init__(*args, **kwargs)

        if 'object_types' in self.fields:
            order_content_types(self.fields['object_types'])


@admin.register(SlackMessage, site=admin_site)
class SlackMessageAdmin(admin.ModelAdmin):
    list_display = ('name',)
    form = SlackMessageForm

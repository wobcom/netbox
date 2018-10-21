from datetime import datetime

from django import forms

from change.models import ChangedField

class ChangeMixin(forms.BaseForm):
    """
    Mix in the change.
    """
    def __init__(self, *args, **kwargs):
        super(ChangeMixin, self).__init__(*args, **kwargs)

        in_change = kwargs.pop('in_change', False)
        change_started = kwargs.pop('change_started', None)
        user = kwargs.pop('user', None)

        if not in_change:
            return

        change_started = datetime.strptime(change_started,
                                          "%Y-%m-%d %H:%M:%S.%f")

        changes = ChangedField.objects.filter(user=user,
                        time__gt=change_started,
                        change_object_type=self.instance.model)

        for change in changes.all():
            self.initial[change.field] = change.new_value

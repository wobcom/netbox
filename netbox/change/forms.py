from datetime import datetime

from django import forms

from change.models import ChangedField

class ChangeMixin(forms.BaseForm):
    """
    Mix in the change.
    """
    def __init__(self, *args, **kwargs):
        super(ChangeMixin, self).__init__(*args, **kwargs)

        # Get the change info
        in_change = kwargs.pop('in_change', False)
        change_started = kwargs.pop('change_started', None)
        user = kwargs.pop('user', None)

        # if were not in a change, we can ignore this mixin
        if not in_change:
            return

        # get the changes we need to apply
        change_started = datetime.strptime(change_started,
                                          "%Y-%m-%d %H:%M:%S.%f")

        changes = ChangedField.objects.filter(user=user,
                        time__gt=change_started,
                        change_object_type=self.instance.model)

        for change in changes.all():
            self.initial[change.field] = change.new_value

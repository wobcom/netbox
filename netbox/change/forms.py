from django import forms

from utilities.forms import BootstrapMixin
from change.models import (
    ChangeInformation, ChangeSet, AffectedCustomer, IN_REVIEW
)

class ChangeInformationForm(BootstrapMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        change_id = kwargs.pop('change_id')
        super().__init__(*args, **kwargs)
        self.fields['depends_on'].queryset = ChangeSet.objects\
                                                      .exclude(pk=change_id)\
                                                      .filter(status=IN_REVIEW)

    class Meta:
        model = ChangeInformation
        fields = '__all__'

AffectedCustomerInlineFormSet = forms.inlineformset_factory(ChangeInformation,
                                                            AffectedCustomer,
                                                            extra=1,
                                                            fields='__all__',
                                                            can_delete=False)

from django import forms

from utilities.forms import BootstrapMixin
from change.models import (
    ChangeInformation, ChangeSet, AffectedCustomer, IN_REVIEW
)


class ChangeInformationForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = ChangeInformation
        fields = '__all__'
        exclude = ['depends_on', '']


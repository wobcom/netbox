from django import forms

from utilities.forms import BootstrapMixin
from change.models import ChangeInformation


class ChangeInformationForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = ChangeInformation
        fields = '__all__'


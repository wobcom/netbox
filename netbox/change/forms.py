from django import forms

from utilities.forms import BootstrapMixin
from change.models import ChangeInformation, AffectedCustomer

class ChangeInformationForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = ChangeInformation
        fields = '__all__'

AffectedCustomerInlineFormSet = forms.inlineformset_factory(ChangeInformation,
                                                            AffectedCustomer,
                                                            extra=1,
                                                            fields='__all__',
                                                            can_delete=False)

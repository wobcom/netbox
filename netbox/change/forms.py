from django.forms import inlineformset_factory

from change.models import ChangeInformation, AffectedCustomer

AffectedCustomerInlineFormSet = inlineformset_factory(ChangeInformation,
                                                      AffectedCustomer,
                                                      extra=1,
                                                      fields='__all__',
                                                      can_delete=False)

from django import forms
from .models import RFIDUser


class RFIDLoginForm(forms.Form):
    """
    Simulates RFID card scan — in production, the RFID reader
    posts the card ID directly to this endpoint.
    """
    rfid_code = forms.CharField(
        max_length=50,
        label="RFID Card Code",
        widget=forms.TextInput(attrs={
            'placeholder': 'Scan RFID card',
            'autofocus': True,
            'class': 'rfid-input',
        })
    )

    def clean_rfid_code(self):
        code = self.cleaned_data['rfid_code'].strip().upper()
        try:
            user = RFIDUser.objects.get(rfid_code=code, is_active=True)
        except RFIDUser.DoesNotExist:
            raise forms.ValidationError("RFID card not recognized or access revoked.")
        return code
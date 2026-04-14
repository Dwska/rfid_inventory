from django import forms


class RFIDLoginForm(forms.Form):
    rfid_code = forms.CharField(
        max_length=100,
        label="RFID Card Code",
        widget=forms.TextInput(attrs={
            'placeholder':  'Scan RFID card or type code...',
            'autofocus':    True,
            'autocomplete': 'off',
            'id':           'rfid-input',
        })
    )

    def clean_rfid_code(self):
        # Strip whitespace, newlines, carriage returns the reader might append
        code = self.cleaned_data['rfid_code'].strip().upper()

        # Remove any non-printable characters (some readers append \r or \x00)
        code = ''.join(c for c in code if c.isprintable())

        if len(code) < 4:
            raise forms.ValidationError("Card code too short — minimum 4 characters.")

        return code
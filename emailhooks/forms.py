from models import EmailHook

from django import forms


class EmailHookForm(forms.ModelForm):
    class Meta:
        model = EmailHook
        fields = ['recipient', 'destination']

    def clean_recipient(self):
        recipient = self.cleaned_data.get('recipient').lower()

        excluded = [
            'webmaster',
            'postmaster',
            'admin',
            'catchall',
        ]

        if (recipient in excluded):
            raise forms.ValidationError('Recipient already taken')
        else:
            return recipient

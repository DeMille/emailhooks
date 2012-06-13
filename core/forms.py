from models import emailHooks
from django import forms

class AddHookForm(forms.Form):
    recipient = forms.SlugField(error_messages={'invalid': 'Please only letters, numbers, underscores or hyphens :(', 'required': 'Forgot something?'})
    script_url = forms.URLField(error_messages={'invalid': "I'll need a valid URL please", 'required': 'Forgot something?'})

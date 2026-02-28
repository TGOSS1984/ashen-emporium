from django import forms


class ContactForm(forms.Form):
    name = forms.CharField(max_length=80, widget=forms.TextInput(attrs={
        "class": "form-control",
        "placeholder": "Your name",
    }))
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        "class": "form-control",
        "placeholder": "you@example.com",
    }))
    order_number = forms.CharField(
        max_length=40,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Optional (e.g. AE-10293)",
        }),
    )
    subject = forms.CharField(max_length=120, widget=forms.TextInput(attrs={
        "class": "form-control",
        "placeholder": "Subject",
    }))
    message = forms.CharField(widget=forms.Textarea(attrs={
        "class": "form-control",
        "placeholder": "Tell us what happened…",
        "rows": 6,
    }))

    # small anti-spam honeypot
    website = forms.CharField(required=False, widget=forms.HiddenInput())

    def clean_website(self):
        val = self.cleaned_data.get("website", "")
        if val:
            raise forms.ValidationError("Spam detected.")
        return val
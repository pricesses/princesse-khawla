from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from partners.models import Partner, PartnerEvent, PartnerAd


class PartnerLoginForm(forms.Form):
    email    = forms.EmailField(widget=forms.EmailInput(attrs={
        'class':       'w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500',
        'placeholder': 'votre@email.com',
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class':       'w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500',
        'placeholder': '••••••••',
    }))

    def clean(self):
        cleaned = super().clean()
        email    = cleaned.get('email')
        password = cleaned.get('password')

        if email and password:
            try:
                partner = Partner.objects.get(email=email, is_active=True)
            except Partner.DoesNotExist:
                raise ValidationError("Email ou mot de passe incorrect.")

            if not partner.check_password(password):
                raise ValidationError("Email ou mot de passe incorrect.")

            if partner.account_frozen:
                raise ValidationError("Votre compte est suspendu pour non-paiement.")

            cleaned['partner'] = partner
        return cleaned


class PartnerEventForm(forms.ModelForm):
    class Meta:
        model  = PartnerEvent
        fields = ['title', 'description', 'start_date', 'end_date', 'link']
        widgets = {
            'title': forms.TextInput(attrs={
                'class':       'w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Titre de l evenement',
            }),
            'description': forms.Textarea(attrs={
                'class':       'w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none',
                'rows':        4,
                'placeholder': 'Description de l evenement...',
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500',
                'type':  'date',
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500',
                'type':  'date',
            }),
            'link': forms.URLInput(attrs={
                'class':       'w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'https://...',
            }),
        }

    def clean_start_date(self):
        start_date = self.cleaned_data.get('start_date')
        if not start_date:
            return start_date
        today = timezone.now().date()
        delta = (start_date - today).days
        if delta < 7:
            raise ValidationError(
                f"La date de debut doit etre au minimum dans 7 jours (actuellement dans {delta} jour(s))."
            )
        return start_date

    def clean(self):
        cleaned    = super().clean()
        start_date = cleaned.get('start_date')
        end_date   = cleaned.get('end_date')
        if start_date and end_date and end_date < start_date:
            raise ValidationError("La date de fin ne peut pas etre avant la date de debut.")
        return cleaned


class PartnerAdForm(forms.ModelForm):
    class Meta:
        model  = PartnerAd
        fields = ['title', 'image', 'redirect_url', 'start_date', 'end_date']
        widgets = {
            'title': forms.TextInput(attrs={
                'class':       'w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Titre de la publicite',
            }),
            'redirect_url': forms.URLInput(attrs={
                'class':       'w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'https://monsite.com/offre',
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500',
                'type':  'date',
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500',
                'type':  'date',
            }),
        }

    def clean_start_date(self):
        start_date = self.cleaned_data.get('start_date')
        if not start_date:
            return start_date
        today = timezone.now().date()
        if start_date <= today:
            raise ValidationError("La date de debut doit etre dans le futur.")
        return start_date

    def clean(self):
        cleaned    = super().clean()
        start_date = cleaned.get('start_date')
        end_date   = cleaned.get('end_date')
        if start_date and end_date:
            if end_date < start_date:
                raise ValidationError("La date de fin ne peut pas etre avant la date de debut.")
            nb_days = (end_date - start_date).days + 1
            if nb_days < 1:
                raise ValidationError("La publicite doit durer au moins 1 jour.")
        return cleaned
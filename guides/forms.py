from django import forms
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from .models import Guide

class GuideSettingsForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={
        'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-xl focus:ring-blue-500 focus:border-blue-500 block w-full p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500 transition-all duration-200',
        'placeholder': 'First Name'
    }))
    last_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={
        'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-xl focus:ring-blue-500 focus:border-blue-500 block w-full p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500 transition-all duration-200',
        'placeholder': 'Last Name'
    }))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-xl focus:ring-blue-500 focus:border-blue-500 block w-full p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500 transition-all duration-200',
        'placeholder': 'email@example.com'
    }))

    class Meta:
        model = Guide
        fields = ['phone', 'photo', 'description', 'languages', 'accepts_children', 'price_adult', 'price_child']
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-xl focus:ring-blue-500 focus:border-blue-500 block w-full p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500 transition-all duration-200',
                'placeholder': '+216 ...'
            }),
            'description': forms.Textarea(attrs={
                'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-xl focus:ring-blue-500 focus:border-blue-500 block w-full p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500 transition-all duration-200',
                'rows': 4,
                'placeholder': 'Tell us about yourself...'
            }),
            'languages': forms.TextInput(attrs={
                'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-xl focus:ring-blue-500 focus:border-blue-500 block w-full p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500 transition-all duration-200',
                'placeholder': 'e.g. Français, Anglais'
            }),
            'price_adult': forms.NumberInput(attrs={
                'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-xl focus:ring-blue-500 focus:border-blue-500 block w-full p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500 transition-all duration-200',
            }),
            'price_child': forms.NumberInput(attrs={
                'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-xl focus:ring-blue-500 focus:border-blue-500 block w-full p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500 transition-all duration-200',
            }),
            'accepts_children': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-blue-600 bg-gray-100 border-gray-300 rounded-lg focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600 transition-all duration-200'
            }),
            'photo': forms.FileInput(attrs={
                'class': 'block w-full text-sm text-gray-900 border border-gray-300 rounded-xl cursor-pointer bg-gray-50 dark:text-gray-400 focus:outline-none dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 p-2'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk or not self.instance.phone:
            self.fields['phone'].initial = '+216 '
            
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.email

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if not photo and not self.instance.photo:
            raise forms.ValidationError(_("La photo de profil est obligatoire."))
        return photo

    def clean_description(self):
        desc = self.cleaned_data.get('description')
        if not desc:
            raise forms.ValidationError(_("La description est obligatoire."))
        return desc


# ── Language choices ───────────────────────────────────────────────────────────
LANGUAGES_CHOICES = [
    ('Arabe',       _('Arabe 🇹🇳')),
    ('Français',    _('Français 🇫🇷')),
    ('Anglais',     _('Anglais 🇬🇧')),
    ('Espagnol',    _('Espagnol 🇪🇸')),
    ('Italien',     _('Italien 🇮🇹')),
    ('Allemand',    _('Allemand 🇩🇪')),
    ('Russe',       _('Russe 🇷🇺')),
    ('Chinois',     _('Chinois 🇨🇳')),
    ('Japonais',    _('Japonais 🇯🇵')),
    ('Portugais',   _('Portugais 🇵🇹')),
    ('Néerlandais', _('Néerlandais 🇳🇱')),
    ('Turc',        _('Turc 🇹🇷')),
]


class GuideAdminForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=False, label=_("Prénom"),
        widget=forms.TextInput(attrs={'autocomplete': 'off'}))
    last_name = forms.CharField(max_length=30, required=False, label=_("Nom"),
        widget=forms.TextInput(attrs={'autocomplete': 'off'}))
    languages_list = forms.MultipleChoiceField(
        choices=LANGUAGES_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_("Langues parlées")
    )
    stars = forms.FloatField(
        required=False, min_value=0, max_value=5,
        label=_("Note initiale (étoiles)"),
        widget=forms.NumberInput(attrs={'step': '0.5', 'min': '0', 'max': '5', 'autocomplete': 'off'})
    )

    class Meta:
        model = Guide
        fields = ['first_name', 'last_name', 'email', 'phone', 'languages',
                  'accepts_children', 'price_adult', 'price_child',
                  'photo', 'description', 'stars']
        widgets = {
            'first_name':  forms.TextInput(attrs={
                'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-xl focus:ring-blue-500 focus:border-blue-500 block w-full p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500 transition-all duration-200',
                'placeholder': 'First Name',
                'autocomplete': 'off'
            }),
            'last_name':   forms.TextInput(attrs={
                'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-xl focus:ring-blue-500 focus:border-blue-500 block w-full p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500 transition-all duration-200',
                'placeholder': 'Last Name',
                'autocomplete': 'off'
            }),
            'email':       forms.EmailInput(attrs={
                'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-xl focus:ring-blue-500 focus:border-blue-500 block w-full p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500 transition-all duration-200',
                'placeholder': 'email@example.com',
                'autocomplete': 'off'
            }),
            'phone':       forms.TextInput(attrs={
                'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-xl focus:ring-blue-500 focus:border-blue-500 block w-full p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500 transition-all duration-200',
                'placeholder': '+216 ...',
                'autocomplete': 'off'
            }),
            'price_adult': forms.NumberInput(attrs={
                'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-xl focus:ring-blue-500 focus:border-blue-500 block w-full p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500 transition-all duration-200',
                'placeholder': '0.0'
            }),
            'price_child': forms.NumberInput(attrs={
                'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-xl focus:ring-blue-500 focus:border-blue-500 block w-full p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500 transition-all duration-200',
                'placeholder': '0.0'
            }),
            'description': forms.Textarea(attrs={
                'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-xl focus:ring-blue-500 focus:border-blue-500 block w-full p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500 transition-all duration-200',
                'rows': 4,
                'placeholder': 'Tell us about the guide...'
            }),
            'languages':   forms.HiddenInput(),
            'accepts_children': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-blue-600 bg-gray-100 border-gray-300 rounded-lg focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600 transition-all duration-200'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk or not self.instance.phone:
            self.fields['phone'].initial = '+216 '

        if self.instance and self.instance.pk and self.instance.user_id:
            try:
                self.fields['first_name'].initial = self.instance.user.first_name
                self.fields['last_name'].initial  = self.instance.user.last_name
            except Exception:
                pass
        # Pre-populate languages checkboxes from the stored CSV string
        if self.instance and self.instance.pk and self.instance.languages:
            saved = [l.strip() for l in self.instance.languages.split(',')]
            self.fields['languages_list'].initial = saved

    def clean(self):
        cleaned_data = super().clean()
        # Merge checkbox selections back into the hidden 'languages' CSV field
        selected = cleaned_data.get('languages_list', [])
        cleaned_data['languages'] = ', '.join(selected)
        return cleaned_data

    def clean_photo(self):
        return self.cleaned_data.get('photo')

    def clean_description(self):
        return self.cleaned_data.get('description')

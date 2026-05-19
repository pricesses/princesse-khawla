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

    # ── Sélecteur de langues identique au formulaire admin ─────────────────
    languages_list = forms.MultipleChoiceField(
        choices=[],          # sera injecté dynamiquement depuis LANGUAGES_CHOICES
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_("Spoken Languages")
    )

    class Meta:
        model = Guide
        fields = ['phone', 'photo', 'description', 'languages', 'accepts_children', 'price_adult', 'price_child', 'preferred_language']
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
            # languages est maintenant caché — alimenté par languages_list
            'languages': forms.HiddenInput(),
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
            # Caché — géré via les boutons radio dans le template
            'preferred_language': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Injecte les choix depuis la constante partagée
        self.fields['languages_list'].choices = LANGUAGES_CHOICES

        if not self.instance.pk or not self.instance.phone:
            self.fields['phone'].initial = '+216 '

        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.email

        # Pré-coche les langues déjà enregistrées
        if self.instance and self.instance.pk and self.instance.languages:
            saved = [l.strip() for l in self.instance.languages.split(',')]
            self.fields['languages_list'].initial = saved

        # Pré-remplit la langue de notification
        if self.instance and self.instance.pk:
            self.fields['preferred_language'].initial = self.instance.preferred_language or 'fr'

    def clean(self):
        cleaned_data = super().clean()
        # Fusionne les cases cochées en chaîne CSV stockée dans `languages`
        selected = cleaned_data.get('languages_list', [])
        cleaned_data['languages'] = ', '.join(selected)
        # Préserve explicitement la langue de notification
        if not cleaned_data.get('preferred_language'):
            cleaned_data['preferred_language'] = self.instance.preferred_language or 'fr'
        return cleaned_data

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

    # ── NOTE ADMIN (remplace l'ancien champ `stars`) ───────────────────────
    # Ce champ alimente admin_stars sur le modèle Guide ET crée/met à jour
    # un enregistrement GuideAdminRating.
    admin_stars = forms.FloatField(
        required=False,
        min_value=0,
        max_value=5,
        label=_("Note Administrateur (étoiles)"),
        widget=forms.NumberInput(attrs={
            'step': '1',
            'min': '0',
            'max': '5',
            'autocomplete': 'off',
            # L'id est utilisé par le JS du template pour le widget étoiles
            'id': 'id_admin_stars',
        })
    )

    class Meta:
        model = Guide
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'languages',
            'accepts_children', 'price_adult', 'price_child',
            'photo', 'description',
            # NE PAS inclure 'stars' ni 'admin_stars' du modèle directement :
            # on passe par le champ de formulaire admin_stars ci-dessus.
        ]
        widgets = {
            'first_name':  forms.TextInput(attrs={
                'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-xl focus:ring-blue-500 focus:border-blue-500 block w-full p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white transition-all duration-200',
                'placeholder': 'First Name', 'autocomplete': 'off'
            }),
            'last_name':   forms.TextInput(attrs={
                'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-xl focus:ring-blue-500 focus:border-blue-500 block w-full p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white transition-all duration-200',
                'placeholder': 'Last Name', 'autocomplete': 'off'
            }),
            'email':       forms.EmailInput(attrs={
                'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-xl focus:ring-blue-500 focus:border-blue-500 block w-full p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white transition-all duration-200',
                'placeholder': 'email@example.com', 'autocomplete': 'off'
            }),
            'phone':       forms.TextInput(attrs={
                'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-xl focus:ring-blue-500 focus:border-blue-500 block w-full p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white transition-all duration-200',
                'placeholder': '+216 ...', 'autocomplete': 'off'
            }),
            'price_adult': forms.NumberInput(attrs={
                'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-xl focus:ring-blue-500 focus:border-blue-500 block w-full p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white transition-all duration-200',
                'placeholder': '0.0'
            }),
            'price_child': forms.NumberInput(attrs={
                'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-xl focus:ring-blue-500 focus:border-blue-500 block w-full p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white transition-all duration-200',
                'placeholder': '0.0'
            }),
            'description': forms.Textarea(attrs={
                'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-xl focus:ring-blue-500 focus:border-blue-500 block w-full p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white transition-all duration-200',
                'rows': 4, 'placeholder': 'Tell us about the guide...'
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

        # Pré-remplit les cases langue depuis le CSV stocké
        if self.instance and self.instance.pk and self.instance.languages:
            saved = [l.strip() for l in self.instance.languages.split(',')]
            self.fields['languages_list'].initial = saved

        # Pré-remplit la note admin depuis admin_stars ou GuideAdminRating
        if self.instance and self.instance.pk:
            try:
                self.fields['admin_stars'].initial = self.instance.admin_rating.rating
            except Exception:
                self.fields['admin_stars'].initial = self.instance.admin_stars or 0.0

    def clean(self):
        cleaned_data = super().clean()
        # Fusionne les cases langue dans le champ CSV caché
        selected = cleaned_data.get('languages_list', [])
        cleaned_data['languages'] = ', '.join(selected)
        return cleaned_data

    def clean_photo(self):
        return self.cleaned_data.get('photo')

    def clean_description(self):
        return self.cleaned_data.get('description')

    def save(self, commit=True):
        """
        Surcharge save() pour propager admin_stars vers :
        1. guide.admin_stars (champ modèle)
        2. GuideAdminRating (table dédiée)
        3. guide.stars (moyenne pondérée globale)
        """
        guide = super().save(commit=False)

        admin_stars_value = self.cleaned_data.get('admin_stars')
        if admin_stars_value is not None:
            guide.admin_stars = round(float(admin_stars_value), 1)

        # Recalcule la note globale avant de sauvegarder
        guide._update_global_stars()

        if commit:
            guide.save()

            # Crée ou met à jour GuideAdminRating
            if admin_stars_value is not None:
                from .models import GuideAdminRating
                GuideAdminRating.objects.update_or_create(
                    guide=guide,
                    defaults={'rating': guide.admin_stars},
                )

        return guide
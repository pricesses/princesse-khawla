from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _
from tinymce.widgets import TinyMCE

from .models import (
    Location,
    ImageLocation,
    Event,
    ImageEvent,
    Tip,
    Hiking,
    HikingLocation,
    ImageHiking,
    Ad,
    ImageAd,
    PublicTransport,
    PublicTransportTime,
    Partner,
    Sponsor,
)
from cities_light.models import City


class FlowbiteFormMixin:
    input_class = (
        "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg "
        "focus:ring-blue-600 focus:border-blue-600 block w-full p-2.5 "
        "dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 "
        "dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"
    )

    file_input_class = (
        "block w-full text-sm text-gray-900 border border-gray-300 rounded-lg "
        "cursor-pointer bg-gray-50 dark:text-gray-400 focus:outline-none "
        "dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400"
    )

    checkbox_class = "w-5 h-5 border border-default-medium rounded bg-neutral-secondary-medium focus:ring-2 focus:ring-brand-soft"
    radio_class = "w-4 h-4 text-blue-600 focus:ring-2 focus:ring-blue-500"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            widget = field.widget
            classes = widget.attrs.get("class", "")

            if isinstance(widget, (forms.CheckboxInput,)):
                widget.attrs["class"] = f"{classes} {self.checkbox_class}".strip()
            elif isinstance(widget, (forms.RadioSelect,)):
                widget.attrs["class"] = f"{classes} {self.radio_class}".strip()
            elif isinstance(widget, (forms.FileInput,)):
                widget.attrs["class"] = f"{classes} {self.file_input_class}".strip()
            else:
                widget.attrs["class"] = f"{classes} {self.input_class}".strip()

            widget.attrs.setdefault("id", f"id_{name}")


class LocationForm(FlowbiteFormMixin, forms.ModelForm):
    name_en = forms.CharField(
        label=_("Name (English)"),
        max_length=255,
        required=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": _("Enter location name in English"),
            }
        ),
        error_messages={
            "required": _("Please enter the name in English."),
        },
    )
    name_fr = forms.CharField(
        label=_("Name (French)"),
        max_length=255,
        required=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": _("Enter location name in French"),
            }
        ),
        error_messages={
            "required": _("Please enter the name in French."),
        },
    )

    story_en = forms.CharField(
        label=_("Story (English)"),
        required=True,
        widget=TinyMCE(attrs={"cols": 80, "rows": 30}),
        error_messages={
            "required": _("Please enter the story in English."),
        },
    )
    story_fr = forms.CharField(
        label=_("Story (French)"),
        required=True,
        widget=TinyMCE(attrs={"cols": 80, "rows": 30}),
        error_messages={
            "required": _("Please enter the story in French."),
        },
    )

    class Meta:
        model = Location
        fields = [
            "name_en",
            "name_fr",
            "category",
            "country",
            "city",
            "latitude",
            "longitude",
            "story_en",
            "story_fr",
            "openFrom",
            "openTo",
            "admissionFee",
            "is_active_ads",
            "closedDays",
        ]
        widgets = {
            "category": forms.Select(
                attrs={
                    "placeholder": _("Select location category"),
                    "required": True,
                }
            ),
            "country": forms.Select(
                attrs={
                    "placeholder": _("Select location country"),
                    "required": True,
                }
            ),
            "city": forms.Select(
                attrs={
                    "placeholder": _("Select location city"),
                    "required": True,
                }
            ),
            "latitude": forms.NumberInput(
                attrs={
                    "placeholder": _("e.g., 36.8065"),
                    "step": "0.000001",
                }
            ),
            "longitude": forms.NumberInput(
                attrs={
                    "placeholder": _("e.g., 10.1815"),
                    "step": "0.000001",
                }
            ),
            "openFrom": forms.TimeInput(
                attrs={
                    "type": "time",
                    "placeholder": _("Opening time"),
                }
            ),
            "openTo": forms.TimeInput(
                attrs={
                    "type": "time",
                    "placeholder": _("Closing time"),
                }
            ),
            "admissionFee": forms.NumberInput(
                attrs={
                    "placeholder": _("e.g., 5.00"),
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "is_active_ads": forms.CheckboxInput(),
            "closedDays": forms.CheckboxSelectMultiple(
                attrs={
                    "class": "w-5 h-5 border border-default-medium rounded bg-neutral-secondary-medium focus:ring-2 focus:ring-brand-soft",
                }
            ),
        }

        error_messages = {
            "category": {
                "required": _("Please select a category."),
            },
            "country": {
                "required": _("Please select a country."),
            },
            "city": {
                "required": _("Please select a city."),
            },
        }

        help_texts = {
            "latitude": _("Latitude in decimal degrees (e.g., 36.8065)"),
            "longitude": _("Longitude in decimal degrees (e.g., 10.1815)"),
            "openFrom": _("Leave empty if location is always open"),
            "openTo": _("Leave empty if location is always open"),
            "admissionFee": _("Leave empty if admission is free"),
            "is_active_ads": _("Enable advertisements for this location"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "category" in self.fields:
            self.fields["category"].required = True
        if "country" in self.fields:
            self.fields["country"].required = True
        if "city" in self.fields:
            self.fields["city"].required = True

        if "city" in self.fields:
            from cities_light.models import City

            if self.instance and self.instance.country:
                self.fields["city"].queryset = City.objects.filter(
                    country=self.instance.country
                )
            else:
                self.fields["city"].queryset = City.objects.all()

    def clean(self):
        cleaned_data = super().clean()

        errors = []

        if not cleaned_data.get("name_en"):
            errors.append(_("Please enter the name in English."))
            if "name_en" in self.errors:
                del self.errors["name_en"]

        if not cleaned_data.get("name_fr"):
            errors.append(_("Please enter the name in French."))
            if "name_fr" in self.errors:
                del self.errors["name_fr"]

        if not cleaned_data.get("story_en"):
            errors.append(_("Please enter the story in English."))
            if "story_en" in self.errors:
                del self.errors["story_en"]

        if not cleaned_data.get("story_fr"):
            errors.append(_("Please enter the story in French."))
            if "story_fr" in self.errors:
                del self.errors["story_fr"]

        for error in errors:
            self.add_error(None, error)

        open_from = cleaned_data.get("openFrom")
        open_to = cleaned_data.get("openTo")

        if open_from and open_to and open_from >= open_to:
            self.add_error("openTo", _("Opening time must be before closing time."))

        return cleaned_data


class ImageLocationForm(forms.ModelForm):
    class Meta:
        model = ImageLocation
        fields = ["image"]
        widgets = {
            "image": forms.FileInput(
                attrs={
                    "class": "block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 dark:text-gray-400 focus:outline-none dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400",
                    "accept": "image/*",
                }
            )
        }


ImageLocationFormSet = inlineformset_factory(
    Location,
    ImageLocation,
    form=ImageLocationForm,
    extra=1,
    can_delete=True,
    max_num=10,
)


class EventForm(FlowbiteFormMixin, forms.ModelForm):
    name_en = forms.CharField(
        label=_("Name (English)"),
        max_length=255,
        required=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": _("Enter event name in English"),
            }
        ),
        error_messages={
            "required": _("Please enter the name in English."),
        },
    )
    name_fr = forms.CharField(
        label=_("Name (French)"),
        max_length=255,
        required=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": _("Enter event name in French"),
            }
        ),
        error_messages={
            "required": _("Please enter the name in French."),
        },
    )

    description_en = forms.CharField(
        label=_("Description (English)"),
        required=True,
        widget=TinyMCE(attrs={"cols": 80, "rows": 30}),
        error_messages={
            "required": _("Please enter the description in English."),
        },
    )
    description_fr = forms.CharField(
        label=_("Description (French)"),
        required=True,
        widget=TinyMCE(attrs={"cols": 80, "rows": 30}),
        error_messages={
            "required": _("Please enter the description in French."),
        },
    )

    link = forms.URLField(
        label=_("Destination Link"),
        required=True,
        widget=forms.URLInput(
            attrs={
                "placeholder": "https://example.com",
            }
        ),
        help_text=_("The destination URL for this event."),
    )

    class Meta:
        model = Event
        fields = [
            "name_en",
            "name_fr",
            "description_en",
            "description_fr",
            "location",
            "city",
            "category",
            "startDate",
            "endDate",
            "time",
            "price",
            "link",
            "boost",
        ]
        widgets = {
            "location": forms.Select(
                attrs={
                    "placeholder": _("Select event location"),
                }
            ),
            "city": forms.Select(
                attrs={
                    "placeholder": _("Select city"),
                }
            ),
            "category": forms.Select(
                attrs={
                    "placeholder": _("Select event category"),
                }
            ),
            "startDate": forms.DateInput(
                attrs={
                    "type": "date",
                    "placeholder": _("Select event start date"),
                }
            ),
            "endDate": forms.DateInput(
                attrs={
                    "type": "date",
                    "placeholder": _("Select event end date"),
                }
            ),
            "time": forms.TimeInput(
                attrs={
                    "type": "time",
                    "placeholder": _("Select event time"),
                }
            ),
            "price": forms.NumberInput(
                attrs={
                    "placeholder": _("Enter event price"),
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "link": forms.URLInput(
                attrs={
                    "placeholder": "https://example.com",
                }
            ),
            "boost": forms.CheckboxInput(),
        }

    def clean(self):
        cleaned_data = super().clean()

        errors = []

        if not cleaned_data.get("name_en"):
            errors.append(_("Please enter the name in English."))
            if "name_en" in self.errors:
                del self.errors["name_en"]

        if not cleaned_data.get("name_fr"):
            errors.append(_("Please enter the name in French."))
            if "name_fr" in self.errors:
                del self.errors["name_fr"]

        if not cleaned_data.get("description_en"):
            errors.append(_("Please enter the description in English."))
            if "description_en" in self.errors:
                del self.errors["description_en"]

        if not cleaned_data.get("description_fr"):
            errors.append(_("Please enter the description in French."))
            if "description_fr" in self.errors:
                del self.errors["description_fr"]

        for error in errors:
            self.add_error(None, error)

        return cleaned_data

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if "city" in self.fields:
            self.fields["city"].required = True

        if user and not (user.is_staff or user.is_superuser):
            if "boost" in self.fields:
                del self.fields["boost"]

        if self.instance and self.instance.pk:
            pass


class ImageEventForm(forms.ModelForm):
    class Meta:
        model = ImageEvent
        fields = ["image"]
        widgets = {
            "image": forms.FileInput(
                attrs={
                    "class": "block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 dark:text-gray-400 focus:outline-none dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400",
                    "accept": "image/*",
                }
            )
        }


ImageEventFormSet = inlineformset_factory(
    Event,
    ImageEvent,
    form=ImageEventForm,
    extra=1,
    can_delete=True,
    max_num=10,
)


class TipForm(FlowbiteFormMixin, forms.ModelForm):
    description_en = forms.CharField(
        label=_("Description (English)"),
        required=True,
        widget=TinyMCE(attrs={"cols": 80, "rows": 30}),
    )
    description_fr = forms.CharField(
        label=_("Description (French)"),
        required=True,
        widget=TinyMCE(attrs={"cols": 80, "rows": 30}),
    )

    class Meta:
        model = Tip
        fields = ["city", "description_en", "description_fr"]
        widgets = {
            "city": forms.Select(
                attrs={
                    "placeholder": _("Select city"),
                    "required": True,
                }
            ),
        }
        error_messages = {
            "city": {
                "required": _("Please select a city."),
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "city" in self.fields:
            self.fields["city"].required = True

    def clean(self):
        cleaned_data = super().clean()
        required_fields = {
            "description_en": _("Description (English) is required."),
            "description_fr": _("Description (French) is required."),
        }

        for field, error in required_fields.items():
            if not cleaned_data.get(field):
                self.add_error(None, error)
                if field in self._errors:
                    del self._errors[field]

        return cleaned_data


class HikingForm(FlowbiteFormMixin, forms.ModelForm):
    name_en = forms.CharField(
        label=_("Name (English)"),
        required=True,
        error_messages={
            "required": _("Please enter the name in English."),
        },
    )
    name_fr = forms.CharField(
        label=_("Name (French)"),
        required=True,
        error_messages={
            "required": _("Please enter the name in French."),
        },
    )
    description_en = forms.CharField(
        label=_("Description (English)"),
        required=True,
        widget=TinyMCE(attrs={"cols": 80, "rows": 30}),
        error_messages={
            "required": _("Please enter the description in English."),
        },
    )
    description_fr = forms.CharField(
        label=_("Description (French)"),
        required=True,
        widget=TinyMCE(attrs={"cols": 80, "rows": 30}),
        error_messages={
            "required": _("Please enter the description in French."),
        },
    )

    class Meta:
        model = Hiking
        fields = [
            "name_en",
            "name_fr",
            "description_en",
            "description_fr",
            "city",
            "latitude",
            "longitude",
        ]
        widgets = {
            "city": forms.Select(
                attrs={
                    "placeholder": _("Select city"),
                    "class": "block w-full px-3 py-2.5 bg-neutral-secondary-medium border border-default-medium text-heading text-sm rounded-base focus:ring-brand focus:border-brand shadow-xs placeholder:text-body",
                    "required": True,
                }
            ),
            "latitude": forms.NumberInput(
                attrs={
                    "placeholder": _("e.g., 36.8065"),
                    "step": "0.000001",
                }
            ),
            "longitude": forms.NumberInput(
                attrs={
                    "placeholder": _("e.g., 10.1815"),
                    "step": "0.000001",
                }
            ),
        }
        error_messages = {
            "city": {
                "required": _("Please select a city."),
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "city" in self.fields:
            self.fields["city"].required = True

    def clean(self):
        cleaned_data = super().clean()

        errors = []
        if not cleaned_data.get("name_en"):
            errors.append(_("Please enter the name in English."))
            if "name_en" in self.errors:
                del self.errors["name_en"]
        if not cleaned_data.get("name_fr"):
            errors.append(_("Please enter the name in French."))
            if "name_fr" in self.errors:
                del self.errors["name_fr"]
        if not cleaned_data.get("description_en"):
            errors.append(_("Please enter the description in English."))
            if "description_en" in self.errors:
                del self.errors["description_en"]
        if not cleaned_data.get("description_fr"):
            errors.append(_("Please enter the description in French."))
            if "description_fr" in self.errors:
                del self.errors["description_fr"]

        for error in errors:
            self.add_error(None, error)

        return cleaned_data


class HikingLocationForm(FlowbiteFormMixin, forms.ModelForm):
    class Meta:
        model = HikingLocation
        fields = ["location", "order"]
        widgets = {
            "location": forms.Select(
                attrs={
                    "class": "block w-full px-3 py-2.5 bg-neutral-secondary-medium border border-default-medium text-heading text-sm rounded-base focus:ring-brand focus:border-brand shadow-xs placeholder:text-body",
                    "placeholder": _("Select location"),
                }
            ),
            "order": forms.HiddenInput(),
        }


HikingLocationFormSet = inlineformset_factory(
    Hiking,
    HikingLocation,
    form=HikingLocationForm,
    extra=1,
    can_delete=True,
    fields=["location", "order"],
)


class ImageHikingForm(forms.ModelForm):
    class Meta:
        model = ImageHiking
        fields = ["image"]
        widgets = {
            "image": forms.FileInput(
                attrs={
                    "class": "block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 dark:text-gray-400 focus:outline-none dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400",
                    "accept": "image/*",
                }
            )
        }


ImageHikingFormSet = inlineformset_factory(
    Hiking,
    ImageHiking,
    form=ImageHikingForm,
    extra=1,
    can_delete=True,
    max_num=10,
)


class AdForm(FlowbiteFormMixin, forms.ModelForm):
    name = forms.CharField(
        label=_("Ad Name"),
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": _("e.g., Summer Campaign 2026"),
            }
        ),
        help_text=_("If empty, a name like 'ADS-XXXXXX' will be auto-generated."),
    )
    link = forms.URLField(
        label=_("Destination Link"),
        required=True,
        widget=forms.URLInput(
            attrs={
                "placeholder": "https://example.com",
            }
        ),
        help_text=_(
            "The destination URL for this ad. This will be tracked via Short.io."
        ),
    )

    class Meta:
        model = Ad
        fields = [
            "name",
            "country",
            "city",
            "image_mobile",
            "image_tablet",
            "link",
            "is_active",
        ]
        widgets = {
            "country": forms.Select(
                attrs={
                    "placeholder": _("Select country"),
                }
            ),
            "city": forms.Select(
                attrs={
                    "placeholder": _("Select city"),
                }
            ),
            "image_mobile": forms.FileInput(attrs={"accept": "image/*"}),
            "image_tablet": forms.FileInput(attrs={"accept": "image/*"}),
            "is_active": forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["is_active"].label = _("Active")

        if "country" in self.fields:
            self.fields["country"].required = True

        if "city" in self.fields:
            self.fields["city"].required = False

        self.fields["image_mobile"].required = True
        self.fields["image_tablet"].required = True

        if self.instance and self.instance.pk:
            self.fields["image_mobile"].required = False
            self.fields["image_tablet"].required = False
            pass

    def clean_image_mobile(self):
        image = self.cleaned_data.get("image_mobile")
        if image:
            if hasattr(image, "image"):
                w, h = image.image.width, image.image.height
            else:
                from django.core.files.images import get_image_dimensions

                w, h = get_image_dimensions(image)

            if w != 320 or h != 50:
                raise forms.ValidationError(
                    _(
                        "Mobile image must be exactly 320x50 pixels. Uploaded: %(w)sx%(h)s"
                    )
                    % {"w": w, "h": h}
                )
        return image

    def clean_image_tablet(self):
        image = self.cleaned_data.get("image_tablet")
        if image:
            if hasattr(image, "image"):
                w, h = image.image.width, image.image.height
            else:
                from django.core.files.images import get_image_dimensions

                w, h = get_image_dimensions(image)

            if w != 728 or h != 90:
                raise forms.ValidationError(
                    _(
                        "Tablet image must be exactly 728x90 pixels. Uploaded: %(w)sx%(h)s"
                    )
                    % {"w": w, "h": h}
                )
        return image


ImageAdFormSet = inlineformset_factory(
    Ad,
    ImageAd,
    fields=["image"],
    extra=1,
    can_delete=True,
    max_num=5,
)


class PartnerForm(FlowbiteFormMixin, forms.ModelForm):
    class Meta:
        model = Partner
        fields = ["name", "image", "link"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "placeholder": _("e.g., Partner name"),
                }
            ),
            "link": forms.URLInput(
                attrs={
                    "placeholder": "https://example.com",
                }
            ),
            "image": forms.FileInput(
                attrs={
                    "accept": "image/*",
                }
            ),
        }
        error_messages = {
            "name": {"required": _("Please enter a name.")},
            "image": {"required": _("Please upload an image (300x200).")},
            "link": {"required": _("Please provide a link.")},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "image" in self.fields:
            self.fields["image"].required = True
            if self.instance and self.instance.pk:
                self.fields["image"].required = False


class SponsorForm(FlowbiteFormMixin, forms.ModelForm):
    class Meta:
        model = Sponsor
        fields = ["name", "image", "link"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "placeholder": _("e.g., Sponsor name"),
                }
            ),
            "link": forms.URLInput(
                attrs={
                    "placeholder": "https://example.com",
                }
            ),
            "image": forms.FileInput(
                attrs={
                    "accept": "image/*",
                }
            ),
        }
        error_messages = {
            "name": {"required": _("Please enter a name.")},
            "image": {"required": _("Please upload an image (300x200).")},
            "link": {"required": _("Please provide a link.")},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "image" in self.fields:
            self.fields["image"].required = True
            if self.instance and self.instance.pk:
                self.fields["image"].required = False


class PublicTransportForm(forms.ModelForm):
    class Meta:
        model = PublicTransport
        fields = (
            "publicTransportType",
            "city",
            "fromCity",
            "toCity",
            "fromRegion",
            "toRegion",
            "busNumber",
            "is_return",
        )
        widgets = {
            "publicTransportType": forms.Select(
                attrs={
                    "placeholder": _("Select transport type"),
                    "required": True,
                    "id": "id_transport_type",
                    "class": "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-600 focus:border-blue-600 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500",
                }
            ),
            "city": forms.Select(
                attrs={
                    "placeholder": _("Select city"),
                    "id": "id_city",
                    "class": "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-600 focus:border-blue-600 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500",
                }
            ),
            "fromCity": forms.Select(
                attrs={
                    "placeholder": _("Select departure city"),
                    "id": "id_from_city",
                    "class": "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-600 focus:border-blue-600 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500",
                }
            ),
            "toCity": forms.Select(
                attrs={
                    "placeholder": _("Select arrival city"),
                    "id": "id_to_city",
                    "class": "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-600 focus:border-blue-600 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500",
                }
            ),
            "fromRegion": forms.Select(
                attrs={
                    "placeholder": _("Select departure region"),
                    "id": "id_from_region",
                    "class": "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-600 focus:border-blue-600 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500",
                }
            ),
            "toRegion": forms.Select(
                attrs={
                    "placeholder": _("Select arrival region"),
                    "id": "id_to_region",
                    "class": "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-600 focus:border-blue-600 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500",
                }
            ),
            "busNumber": forms.TextInput(
                attrs={
                    "placeholder": _("e.g., Line 32, Train 105, or Metro L1"),
                    "id": "id_busNumber",
                    "class": "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-600 focus:border-blue-600 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500",
                }
            ),
            "is_return": forms.CheckboxInput(
                attrs={
                    "id": "id_is_return",
                    "class": "w-5 h-5 border border-gray-300 rounded bg-gray-50 focus:ring-3 focus:ring-blue-300 dark:bg-gray-700 dark:border-gray-600 dark:focus:ring-blue-600",
                }
            ),
        }
        error_messages = {
            "publicTransportType": {
                "required": _("Please select a transport type."),
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        from cities_light.models import SubRegion

        if "publicTransportType" in self.fields:
            self.fields["publicTransportType"].required = True

        # ✅ PERFORMANCE: Restrict cities to Tunisia only instead of all world cities.
        # cities_light has tens of thousands of cities globally — loading them all
        # makes the page very slow and generates a huge HTML select.
        # Change "Tunisia" to your target country name if needed.
        tunisia_cities_qs = City.objects.filter(
            country__name="Tunisia"
        ).select_related("country", "region").order_by("name")

        for field_name in ("city", "fromCity", "toCity"):
            if field_name in self.fields:
                self.fields[field_name].required = False
                self.fields[field_name].queryset = tunisia_cities_qs

        # ✅ PERFORMANCE: Smart region queryset based on context:
        #   - POST (form submitted): use all() so AJAX-loaded IDs pass validation
        #   - GET edit mode: pre-populate with the instance's relevant regions
        #   - GET create mode: empty queryset — AJAX will populate on city change
        if args and args[0]:
            # POST: data is being submitted — accept any SubRegion id
            region_qs = SubRegion.objects.all()
        elif self.instance and self.instance.pk:
            # GET edit mode: load regions relevant to this transport
            if self.instance.city:
                region_qs = SubRegion.objects.filter(
                    region=self.instance.city.region
                ).order_by("name")
            elif self.instance.fromRegion:
                region_qs = SubRegion.objects.filter(
                    region=self.instance.fromRegion.region
                ).order_by("name")
            else:
                region_qs = SubRegion.objects.none()
        else:
            # GET create mode: empty — regions loaded via AJAX
            region_qs = SubRegion.objects.none()

        if "fromRegion" in self.fields:
            self.fields["fromRegion"].required = False
            self.fields["fromRegion"].queryset = region_qs

        if "toRegion" in self.fields:
            self.fields["toRegion"].required = False
            self.fields["toRegion"].queryset = region_qs

        # busNumber is never required at field level; clean() enforces it for bus only.
        if "busNumber" in self.fields:
            self.fields["busNumber"].required = False

    def clean(self):
        cleaned_data = super().clean()

        transport_type = cleaned_data.get("publicTransportType")
        city         = cleaned_data.get("city")
        from_city    = cleaned_data.get("fromCity")
        to_city      = cleaned_data.get("toCity")
        from_region  = cleaned_data.get("fromRegion")
        to_region    = cleaned_data.get("toRegion")
        bus_number   = cleaned_data.get("busNumber", "").strip()

        if not transport_type:
            return cleaned_data

        type_name = transport_type.name.lower().strip()

        # ══════════════════════════════════════════════
        #   BUS: city + fromRegion + toRegion + busNumber required
        # ══════════════════════════════════════════════
        if "bus" in type_name:
            if not city:
                self.add_error("city", _("City is required for bus routes."))
            if not from_region:
                self.add_error("fromRegion", _("Departure region is required for bus."))
            if not to_region:
                self.add_error("toRegion", _("Arrival region is required for bus."))
            if not bus_number:
                self.add_error("busNumber", _("Bus number is required."))

            # Clear unused fields for bus
            cleaned_data["fromCity"] = None
            cleaned_data["toCity"] = None

        # ══════════════════════════════════════════════
        #   TRAIN: fromCity + toCity required
        #   busNumber is optional (train has no line number requirement)
        #   NOTE: The JS hides busNumber for train, so we do NOT require it here.
        # ══════════════════════════════════════════════
        elif "train" in type_name:
            if not from_city:
                self.add_error("fromCity", _("Departure station is required for trains."))
            if not to_city:
                self.add_error("toCity", _("Arrival station is required for trains."))

            # Clear unused fields for train
            cleaned_data["city"]       = None
            cleaned_data["fromRegion"] = None
            cleaned_data["toRegion"]   = None
            # busNumber kept as-is (optional for train)

        # ══════════════════════════════════════════════
        #   METRO: (fromCity + toCity) XOR (fromRegion + toRegion)
        #   busNumber is optional (JS hides it for metro)
        #   NOTE: The JS hides busNumber for metro, so we do NOT require it here.
        # ══════════════════════════════════════════════
        elif "metro" in type_name:
            has_cities  = bool(from_city and to_city)
            has_regions = bool(from_region and to_region)

            if has_cities and has_regions:
                self.add_error(
                    None,
                    _(
                        "For metro: select EITHER (departure + arrival cities) OR "
                        "(departure + arrival regions), but NOT both."
                    ),
                )
                self.add_error("fromCity",   _("Cannot select both cities and regions."))
                self.add_error("fromRegion", _("Cannot select both cities and regions."))

            elif has_cities:
                # Cities selected → clear regions
                cleaned_data["fromRegion"] = None
                cleaned_data["toRegion"]   = None

            elif has_regions:
                # Regions selected → clear cities
                cleaned_data["fromCity"] = None
                cleaned_data["toCity"]   = None

            else:
                self.add_error(
                    None,
                    _(
                        "For metro: select either (departure + arrival cities) OR "
                        "(departure + arrival regions)."
                    ),
                )

            # city field is never used for metro
            cleaned_data["city"] = None

        return cleaned_data


class PublicTransportTimeForm(forms.ModelForm):
    class Meta:
        model = PublicTransportTime
        fields = ["time"]
        widgets = {
            "time": forms.TimeInput(
                attrs={
                    "type": "time",
                    "placeholder": _("Select time"),
                    "class": "bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-600 focus:border-blue-600 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500",
                }
            ),
        }


PublicTransportFormSet = inlineformset_factory(
    PublicTransport,
    PublicTransportTime,
    form=PublicTransportTimeForm,
    extra=1,
    can_delete=True,
    max_num=20,
)
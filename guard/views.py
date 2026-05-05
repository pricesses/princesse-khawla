from django.http import HttpResponseRedirect, Http404, JsonResponse, HttpResponse
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import (
    CreateView, UpdateView, DeleteView,
    ListView, TemplateView, DetailView,
    
)
from partners.models import Receipt
from django.core.cache import cache
from django.db.models.functions import TruncDay
from django.urls import reverse_lazy
from django.utils import timezone
from django.shortcuts import redirect, get_object_or_404, render
from django.views import View
from django.db import models
from django.db.models import Sum, F
from django.core import signing
from django.utils.decorators import method_decorator
from django.utils.translation import get_language, gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal
from django.conf import settings
import datetime
import requests
import uuid
from .models import Location
import secrets
import string
import threading
import logging
logger = logging.getLogger(__name__)

from shared.models import UserProfile
try:
    from shared.models import City, SubRegion
except ImportError:
    City = SubRegion = None

from .forms import (
    LocationForm, ImageLocationFormSet,
    EventForm, ImageEventFormSet,
    TipForm,
    HikingForm, HikingLocationFormSet, ImageHikingFormSet,
    AdForm,
    PublicTransportForm, PublicTransportFormSet,
    PartnerForm, SponsorForm,
)
from .models import (
    LocationCategory, Location,EventCategory,
    Event, Tip,
    Hiking, Ad,
    PublicTransport,PublicTransportType,
    LegacyPartner, Partner, Sponsor, AdClick, EventClick,
)
from datetime import timedelta
from shared.short_io import ShortIOService



try:
    from partners.models import PartnerEvent, PartnerAd, Partner as PartnerAccount
except ImportError:
    PartnerEvent = PartnerAd = PartnerAccount = None

try:
    from shared.utils import send_validation_email
except ImportError:
    send_validation_email = None

try:
    from shared.services import ShortIOService, KonnectService
except ImportError:
    ShortIOService = KonnectService = None

# ── API HELPERS ───────────────────────────────────────────────────────────────

def get_cities_by_country(request, country_id=None):
    c_id = country_id or request.GET.get('country_id')
    if City and c_id:
        cities = City.objects.filter(country_id=c_id).order_by('name')
        return JsonResponse([{'id': c.id, 'name': c.name} for c in cities], safe=False)
    return JsonResponse([], safe=False)

def get_subregions_by_city(request, city_id=None):
    c_id = city_id or request.GET.get('city_id')
    if SubRegion and c_id:
        subregions = SubRegion.objects.filter(city_id=c_id).order_by('name')
        return JsonResponse([{'id': s.id, 'name': s.name} for s in subregions], safe=False)
    return JsonResponse([], safe=False)

def get_all_subregions(request):
    if SubRegion:
        subregions = SubRegion.objects.all().order_by('name')
        return JsonResponse([{'id': s.id, 'name': s.name} for s in subregions], safe=False)
    return JsonResponse([], safe=False)

def get_locations_by_city(request, city_id=None):
    c_id = city_id or request.GET.get('city')
    category_ids = request.GET.getlist('category')
    
    if Location and c_id:
        locations = Location.objects.filter(city_id=c_id).order_by('name')
        if category_ids:
            # Convert to integers to be safe
            try:
                category_ids = [int(cid) for cid in category_ids if cid]
                locations = locations.filter(category_id__in=category_ids)
            except ValueError:
                pass
        
        return JsonResponse([{'id': l.id, 'name': l.name} for l in locations], safe=False)
    return JsonResponse([], safe=False)

def get_schedules(request):
    return JsonResponse({'status': 'feature_not_implemented'}, status=200)

# ── MIXINS ────────────────────────────────────────────────────────────────────

class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_active and (
            self.request.user.is_staff or self.request.user.is_superuser
        )

# ── DASHBOARD ─────────────────────────────────────────────────────────────────

class DashboardView(StaffRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "guard/views/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["db_stats"] = {
            "total_locations": Location.objects.count(),
            "total_events": Event.objects.count(),
            "total_ads": Ad.objects.count(),
        }
        return context

# ── LOCATIONS ─────────────────────────────────────────────────────────────────

class LocationsListView(StaffRequiredMixin, LoginRequiredMixin, ListView):
    model = Location
    template_name = "guard/views/locations/list.html"
    context_object_name = "locations"

class LocationCreateView(StaffRequiredMixin, LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Location
    form_class = LocationForm
    template_name = "guard/views/locations/index.html"
    success_url = reverse_lazy("guard:locationsList")
    success_message = _("Lieu créé.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["image_formset"] = ImageLocationFormSet(
            self.request.POST or None,
            self.request.FILES or None,
            instance=self.object if hasattr(self, 'object') else None
        )
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        if context["image_formset"].is_valid():
            self.object = form.save()
            context["image_formset"].instance = self.object
            context["image_formset"].save()
            return super().form_valid(form)
        return self.form_invalid(form)

class LocationUpdateView(LocationCreateView, UpdateView):
    success_message = _("Lieu mis à jour.")

class LocationDeleteView(StaffRequiredMixin, LoginRequiredMixin, DeleteView):
    model = Location
    success_url = reverse_lazy("guard:locationsList")

# =============================================================================
# EVENTS — STAFF (your original views, kept intact)
# =============================================================================

class EventListView(StaffRequiredMixin, LoginRequiredMixin, ListView):
    model = Event
    template_name = "guard/views/events/list.html"
    context_object_name = "events"

class EventCreateView(StaffRequiredMixin, LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Event
    form_class = EventForm
    template_name = "guard/views/events/index.html"
    success_url = reverse_lazy("guard:eventsList")
    success_message = _("Événement créé.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["image_formset"] = ImageEventFormSet(
            self.request.POST or None,
            self.request.FILES or None,
            instance=self.object if hasattr(self, 'object') else None
        )
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        if context["image_formset"].is_valid():
            self.object = form.save()
            context["image_formset"].instance = self.object
            context["image_formset"].save()
            return super().form_valid(form)
        return self.form_invalid(form)

class EventUpdateView(EventCreateView, UpdateView):
    success_message = _("Événement mis à jour.")

class EventDeleteView(StaffRequiredMixin, LoginRequiredMixin, DeleteView):
    model = Event
    success_url = reverse_lazy("guard:eventsList")

# =============================================================================
# EVENTS — PARTNER-FACING (AJOUT ISLEM)
# =============================================================================

class PartnerEventListView(LoginRequiredMixin, ListView):
    model = Event
    template_name = "guard/views/events/list.html"
    context_object_name = "events"
    ordering = ["-created_at"]

    def get_queryset(self):
        return super().get_queryset().filter(partner=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.request.user.is_staff and ShortIOService:
            service = ShortIOService()
            for obj in context["events"]:
                if obj.short_id:
                    try:
                        clicks = service.get_clicks(obj.short_id)
                        if clicks != obj.clicks:
                            obj.clicks = clicks
                            obj.save(update_fields=["clicks"])
                    except Exception:
                        pass
        return context


class PartnerEventCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Event
    template_name = "guard/views/events/index.html"
    form_class = EventForm
    success_url = reverse_lazy("guard:eventsList")
    success_message = _("Event created successfully.")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["image_formset"] = (
            ImageEventFormSet(self.request.POST, self.request.FILES)
            if self.request.POST else ImageEventFormSet()
        )
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        image_formset = context["image_formset"]
        if image_formset.is_valid():
            has_image = any(
                f.cleaned_data.get("image") and not f.cleaned_data.get("DELETE", False)
                for f in image_formset if f.cleaned_data
            )
            if not has_image:
                form.add_error(None, _("Veuillez télécharger au moins une image."))
                return self.form_invalid(form)
            self.object = form.save(commit=False)
            self.object.client = self.request.user.profile
            if ShortIOService:
                try:
                    service = ShortIOService()
                    short_data = service.shorten_url(self.object.link, title="Event Campaign")
                    if short_data:
                        self.object.short_link = short_data.get("secureShortURL") or short_data.get("shortURL")
                        self.object.short_id   = short_data.get("idString")
                except Exception as e:
                    logger.error(f"Short.io error: {e}")
            self.object.save()
            image_formset.instance = self.object
            image_formset.save()
            messages.success(self.request, self.success_message)
            return HttpResponseRedirect(self.get_success_url())
        return self.form_invalid(form)


class PartnerEventUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Event
    template_name = "guard/views/events/index.html"
    form_class = EventForm
    success_url = reverse_lazy("guard:eventsList")
    success_message = _("Event updated successfully.")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_queryset(self):
        return super().get_queryset().filter(client=self.request.user.profile)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["image_formset"] = (
            ImageEventFormSet(self.request.POST, self.request.FILES, instance=self.object)
            if self.request.POST else ImageEventFormSet(instance=self.object)
        )
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        image_formset = context["image_formset"]
        if image_formset.is_valid():
            existing = sum(1 for f in image_formset if f.instance.pk and not f.cleaned_data.get("DELETE", False))
            new      = sum(1 for f in image_formset if f.cleaned_data.get("image") and not f.instance.pk)
            if existing + new < 1:
                form.add_error(None, _("Veuillez conserver ou télécharger au moins une image."))
                return self.form_invalid(form)
            self.object = form.save(commit=False)
            if "link" in form.changed_data and ShortIOService:
                try:
                    service = ShortIOService()
                    updated = False
                    if self.object.short_id:
                        result = service.update_link(self.object.short_id, self.object.link, title="Event Campaign")
                        if result:
                            self.object.short_link = result.get("secureShortURL") or result.get("shortURL")
                            updated = True
                    if not updated:
                        short_data = service.shorten_url(self.object.link, title="Event Campaign")
                        if short_data:
                            self.object.short_link = short_data.get("secureShortURL") or short_data.get("shortURL")
                            self.object.short_id   = short_data.get("idString")
                except Exception as e:
                    logger.error(f"Short.io error: {e}")
            self.object.save()
            image_formset.instance = self.object
            image_formset.save()
            messages.success(self.request, self.success_message)
            return HttpResponseRedirect(self.get_success_url())
        return self.form_invalid(form)


class PartnerEventTrackingView(UserPassesTestMixin, LoginRequiredMixin, DetailView):
    model = Event
    template_name = "guard/views/events/partials/tracking.html"
    context_object_name = "object"

    def get_queryset(self):
        return super().get_queryset().filter(client=self.request.user.profile)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        period  = self.request.GET.get("period", "today")
        context["period"]     = period
        context["page_title"] = self.object.name
        if self.object.short_id and not self.request.user.is_staff and ShortIOService:
            context["stats"] = ShortIOService().get_link_statistics(self.object.short_id, period)
        return context

    def test_func(self):
        return not self.request.user.is_staff


class PartnerEventDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Event
    success_url = reverse_lazy("guard:eventsList")
    success_message = _("Unfortunately, this event has been deleted")

    def get_queryset(self):
        return super().get_queryset().filter(client=self.request.user.profile)

    def delete(self, request, *args, **kwargs):
        messages.warning(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)

# =============================================================================
# ADS — STAFF (your original views, kept intact)
# =============================================================================

class AdListView(StaffRequiredMixin, LoginRequiredMixin, ListView):
    model = Ad
    template_name = "guard/views/ads/list.html"
    context_object_name = "ads"

class AdCreateView(StaffRequiredMixin, LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Ad
    form_class = AdForm
    template_name = "guard/views/ads/index.html"
    success_url = reverse_lazy("guard:adsList")
    success_message = _("Publicité créée.")

class AdUpdateView(AdCreateView, UpdateView):
    success_message = _("Publicité mise à jour.")

class AdDeleteView(StaffRequiredMixin, LoginRequiredMixin, DeleteView):
    model = Ad
    template_name = "guard/views/ads/partials/confirm_model.html"
    success_url = reverse_lazy("guard:adsList")

# =============================================================================
# ADS — PARTNER-FACING (AJOUT ISLEM)
# =============================================================================

class PartnerAdListView(LoginRequiredMixin, ListView):
    model = Ad
    template_name = "guard/views/ads/list.html"
    context_object_name = "ads"
    ordering = ["-created_at"]

    def get_queryset(self):
        return super().get_queryset().filter(client=self.request.user.profile)


class PartnerAdCreateView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'guard/views/ads/form.html', {'form': AdForm()})

    def post(self, request):
        form    = AdForm(request.POST, request.FILES)
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if form.is_valid():
            ad             = form.save(commit=False)
            ad.client      = request.user.profile
            ad.total_price = form.cleaned_data.get('total_price', Decimal('0'))
            ad.save()
            if is_ajax:
                return JsonResponse({'ok': True, 'ad_id': ad.pk})
            messages.success(request, _("Pub créée. Complétez le paiement pour l'activer."))
            return redirect('guard:partner_ads_list')

        if is_ajax:
            return JsonResponse({'ok': False, 'errors': {f: e.get_json_data() for f, e in form.errors.items()}}, status=400)

        return render(request, 'guard/views/ads/form.html', {'form': form})


class PartnerAdUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model           = Ad
    form_class      = AdForm
    template_name   = "guard/views/ads/form.html"
    success_url     = reverse_lazy("guard:partner_ads_list")
    success_message = _("Pub mise à jour avec succès")

    def dispatch(self, request, *args, **kwargs):
        ad = self.get_object()
        if ad.is_paid:
            messages.error(request, _("Cette pub est verrouillée après paiement. Aucune modification possible."))
            return redirect('guard:partner_ads_list')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return super().get_queryset().filter(client=self.request.user.profile)

    def form_valid(self, form):
        self.object             = form.save(commit=False)
        self.object.total_price = form.cleaned_data.get('total_price', self.object.total_price)
        is_ajax = self.request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if "link" in form.changed_data and ShortIOService:
            try:
                service = ShortIOService()
                updated = False
                if self.object.short_id:
                    result = service.update_link(self.object.short_id, self.object.link, title="Ad Campaign")
                    if result:
                        self.object.short_link = result.get("secureShortURL") or result.get("shortURL")
                        updated = True
                if not updated:
                    short_data = service.shorten_url(self.object.link, title="Ad Campaign")
                    if short_data:
                        self.object.short_link = short_data.get("secureShortURL") or short_data.get("shortURL")
                        self.object.short_id   = short_data.get("idString")
                        self.object.clicks     = 0
            except Exception as e:
                logger.error(f"Short.io error: {e}")

        self.object.save()
        if is_ajax:
            return JsonResponse({'ok': True, 'ad_id': self.object.pk})

        messages.success(self.request, self.success_message)
        return HttpResponseRedirect(self.get_success_url())


class PartnerAdDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model       = Ad
    success_url = reverse_lazy("guard:partner_ads_list")
    success_message = _("Ad deleted successfully")

    def get_queryset(self):
        return super().get_queryset().filter(client=self.request.user.profile)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)


class PartnerAdTrackingView(UserPassesTestMixin, LoginRequiredMixin, DetailView):
    model = Ad
    template_name = "guard/views/ads/partials/tracking.html"
    context_object_name = "object"

    def get_queryset(self):
        return super().get_queryset().filter(client=self.request.user.profile)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        period  = self.request.GET.get("period", "today")
        context["period"]     = period
        context["page_title"] = self.object.link
        if self.object.short_id and not self.request.user.is_staff and ShortIOService:
            context["stats"] = ShortIOService().get_link_statistics(self.object.short_id, period)
        return context

    def test_func(self):
        return not self.request.user.is_staff


class AdsDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "guard/views/ads/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx     = super().get_context_data(**kwargs)
        profile = self.request.user.profile
        today   = timezone.now().date()

        Ad.objects.filter(client=profile, is_paid=True, endDate__lt=today).exclude(
            status=Ad.Status.FINISHED
        ).update(status=Ad.Status.FINISHED)

        qs = Ad.objects.filter(client=profile)
        ctx['total_ads']    = qs.count()
        ctx['active_ads']   = qs.filter(status=Ad.Status.ACTIVE).count()
        ctx['finished_ads'] = qs.filter(status=Ad.Status.FINISHED).count()
        ctx['pending_ads']  = qs.filter(status=Ad.Status.PENDING_PAYMENT).count()
        ctx['total_clicks'] = qs.aggregate(t=Sum(F('db_clicks_count') + F('clicks')))['t'] or 0
        ctx['total_spent']  = qs.filter(is_paid=True).aggregate(t=Sum('total_price'))['t'] or Decimal('0')
        ctx['recent_ads']   = qs.order_by('-created_at')[:10]
        return ctx


# =============================================================================
# ADS — KONNECT PAYMENT (AJOUT ISLEM)
# =============================================================================

class CreateCheckoutSessionView(LoginRequiredMixin, View):

    DAILY_RATE_TND = Decimal('15.000')

    def post(self, request, pk, *args, **kwargs):
        ad = get_object_or_404(Ad, pk=pk, client=request.user.profile)

        if ad.is_paid:
            return JsonResponse({'error': 'Cette pub est déjà payée.'}, status=400)
        if not ad.startDate or not ad.endDate:
            return JsonResponse({'error': 'Les dates ne sont pas définies.'}, status=400)

        today = timezone.now().date()
        if ad.startDate <= today:
            return JsonResponse({'error': 'La date de début doit être demain au minimum.'}, status=400)
        if ad.endDate <= ad.startDate:
            return JsonResponse({'error': 'La date de fin doit être après la date de début.'}, status=400)

        days           = (ad.endDate - ad.startDate).days
        ad.total_price = Decimal(str(days)) * self.DAILY_RATE_TND
        ad.save(update_fields=['total_price'])

        # MODE TEST : confirme directement sans Konnect
        ad.is_paid = True
        ad.sync_status()
        ad.save(update_fields=['is_paid', 'status'])

        success_url = request.build_absolute_uri(
            f'/guard/ads/{ad.pk}/confirm-payment/?payment_ref=TEST-{ad.pk}'
        )
        return JsonResponse({'url': success_url})


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(View):

    def post(self, request, *args, **kwargs):
        import json
        try:
            data        = json.loads(request.body)
            payment_ref = data.get("payment_ref") or data.get("paymentRef") or data.get("ref")
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Konnect webhook : body invalide — {e}")
            return HttpResponse(status=400)

        if not payment_ref:
            logger.warning("Konnect webhook : payment_ref manquant")
            return HttpResponse(status=400)

        if KonnectService:
            service          = KonnectService()
            confirmed_status = service.get_payment_status(payment_ref)

            if confirmed_status == "completed":
                try:
                    ad         = Ad.objects.get(payment_ref=payment_ref)
                    ad.is_paid = True
                    ad.sync_status()
                    ad.save(update_fields=['is_paid', 'status'])
                    logger.info(f"Pub {ad.pk} confirmée via webhook Konnect.")
                except Ad.DoesNotExist:
                    logger.error(f"Webhook Konnect : aucune pub avec payment_ref={payment_ref}")

        return HttpResponse(status=200)


class AdConfirmPaymentView(LoginRequiredMixin, View):

    def get(self, request, pk, *args, **kwargs):
        payment_ref = request.GET.get('payment_ref') or request.GET.get('paymentRef')
        ad          = get_object_or_404(Ad, pk=pk, client=request.user.profile)

        if payment_ref and not ad.is_paid and KonnectService:
            service = KonnectService()
            status  = service.get_payment_status(payment_ref)
            if status == "completed":
                ad.is_paid     = True
                ad.payment_ref = payment_ref
                ad.sync_status()
                ad.save(update_fields=['is_paid', 'status', 'payment_ref'])

        # Mode test : payment_ref commence par TEST-
        if payment_ref and payment_ref.startswith('TEST-') and not ad.is_paid:
            ad.is_paid = True
            ad.sync_status()
            ad.save(update_fields=['is_paid', 'status'])

        if ad.is_paid:
            messages.success(request, _("Paiement confirmé ! Votre pub est maintenant active et verrouillée."))
        else:
            messages.warning(request, _("Le paiement est en cours de traitement. Veuillez patienter."))

        return redirect('guard:partner_ads_list')

# =============================================================================
# TIPS (AJOUT ISLEM — now with UserPassesTestMixin + proper CRUD)
# =============================================================================

class TipsListView(UserPassesTestMixin, LoginRequiredMixin, ListView):
    model = Tip
    template_name = "guard/views/tips/list.html"
    context_object_name = "tips"
    ordering = ["-created_at"]
    def test_func(self): return self.request.user.is_staff


class TipCreateView(UserPassesTestMixin, LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Tip
    form_class = TipForm
    template_name = "guard/views/tips/index.html"
    success_url = reverse_lazy("guard:tipsList")
    success_message = _("Tip created successfully")

    def form_invalid(self, form):
        messages.error(self.request, _("Error creating tip. Please check the form."))
        return super().form_invalid(form)

    def test_func(self): return self.request.user.is_staff


class TipUpdateView(UserPassesTestMixin, LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Tip
    form_class = TipForm
    template_name = "guard/views/tips/index.html"
    success_url = reverse_lazy("guard:tipsList")
    success_message = _("Tip updated successfully")

    def form_invalid(self, form):
        messages.error(self.request, _("Error updating tip. Please check the form."))
        return super().form_invalid(form)

    def test_func(self): return self.request.user.is_staff


class TipDeleteView(UserPassesTestMixin, LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Tip
    success_url = reverse_lazy("guard:tipsList")
    success_message = _("Tip deleted successfully")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)

    def test_func(self): return self.request.user.is_staff

# =============================================================================
# HIKING (AJOUT ISLEM — full CRUD with image + location formsets)
# =============================================================================

class HikingListView(UserPassesTestMixin, LoginRequiredMixin, ListView):
    model = Hiking
    template_name = "guard/views/hiking/list.html"
    context_object_name = "hikings"
    ordering = ["-created_at"]
    def test_func(self): return self.request.user.is_staff


class HikingCreateView(UserPassesTestMixin, LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Hiking
    form_class = HikingForm
    template_name = "guard/views/hiking/index.html"
    success_url = reverse_lazy("guard:hikingsList")
    success_message = _("Hiking created successfully")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["image_formset"]    = ImageHikingFormSet(self.request.POST, self.request.FILES)
            context["location_formset"] = HikingLocationFormSet(self.request.POST)
        else:
            context["image_formset"]    = ImageHikingFormSet()
            context["location_formset"] = HikingLocationFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        image_formset    = context["image_formset"]
        location_formset = context["location_formset"]
        if image_formset.is_valid() and location_formset.is_valid():
            has_image = any(
                f.cleaned_data.get("image") and not f.cleaned_data.get("DELETE", False)
                for f in image_formset if f.cleaned_data
            )
            if not has_image:
                form.add_error(None, _("Please upload at least one image."))
                return self.form_invalid(form)
            self.object = form.save()
            image_formset.instance    = self.object
            location_formset.instance = self.object
            image_formset.save()
            location_formset.save()
            return super().form_valid(form)
        return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("Error creating hiking. Please check the form."))
        return super().form_invalid(form)

    def test_func(self): return self.request.user.is_staff


class HikingUpdateView(UserPassesTestMixin, LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Hiking
    form_class = HikingForm
    template_name = "guard/views/hiking/index.html"
    success_url = reverse_lazy("guard:hikingsList")
    success_message = _("Hiking updated successfully")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["image_formset"]    = ImageHikingFormSet(self.request.POST, self.request.FILES, instance=self.object)
            context["location_formset"] = HikingLocationFormSet(self.request.POST, instance=self.object)
        else:
            context["image_formset"]    = ImageHikingFormSet(instance=self.object)
            context["location_formset"] = HikingLocationFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        image_formset    = context["image_formset"]
        location_formset = context["location_formset"]
        if image_formset.is_valid() and location_formset.is_valid():
            existing = sum(1 for f in image_formset if f.instance.pk and not f.cleaned_data.get("DELETE", False))
            new      = sum(1 for f in image_formset if f.cleaned_data.get("image") and not f.instance.pk)
            if existing + new < 1:
                form.add_error(None, _("Veuillez conserver ou télécharger au moins une image."))
                return self.form_invalid(form)
            self.object = form.save()
            image_formset.instance    = self.object
            location_formset.instance = self.object
            image_formset.save()
            location_formset.save()
            return super().form_valid(form)
        return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("Error updating hiking. Please check the form."))
        return super().form_invalid(form)

    def test_func(self): return self.request.user.is_staff


class HikingDeleteView(UserPassesTestMixin, LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Hiking
    success_url = reverse_lazy("guard:hikingsList")
    success_message = _("Hiking deleted successfully")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)

    def test_func(self): return self.request.user.is_staff

# =============================================================================
# PUBLIC TRANSPORT (AJOUT ISLEM — full CRUD with time formset)
# =============================================================================

def _apply_transport_type_logic(form, request, instance=None):
    """Helper to apply transport type filtering logic to a form."""
    return form


class PublicTransportListView(UserPassesTestMixin, LoginRequiredMixin, ListView):
    model = PublicTransport
    template_name = "guard/views/publicTransports/list.html"
    context_object_name = "transports"
    ordering = ["-created_at"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import PublicTransportType
        context["transport_types"] = PublicTransportType.objects.all()
        return context

    def test_func(self):
        return self.request.user.is_staff


class PublicTransportCreateView(UserPassesTestMixin, LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = PublicTransport
    template_name = "guard/views/publicTransports/index.html"
    form_class = PublicTransportForm
    success_url = reverse_lazy("guard:publicTransportsList")
    success_message = _("Public transport created successfully.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["time_formset"] = (
            PublicTransportFormSet(self.request.POST)
            if self.request.POST else PublicTransportFormSet()
        )
        return context

    def get_form(self, form_class=None):
        return _apply_transport_type_logic(super().get_form(form_class), self.request)

    def form_valid(self, form):
        context = self.get_context_data()
        time_formset = context["time_formset"]
        if time_formset.is_valid():
            has_time = any(
                f.cleaned_data.get("time") and not f.cleaned_data.get("DELETE", False)
                for f in time_formset if f.cleaned_data
            )
            if not has_time:
                form.add_error(None, _("Please add at least one departure time."))
                return self.form_invalid(form)
            self.object = form.save()
            time_formset.instance = self.object
            time_formset.save()
            return super().form_valid(form)
        return self.form_invalid(form)

    def test_func(self):
        return self.request.user.is_staff


class PublicTransportUpdateView(UserPassesTestMixin, LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = PublicTransport
    template_name = "guard/views/publicTransports/index.html"
    form_class = PublicTransportForm
    success_url = reverse_lazy("guard:publicTransportsList")
    success_message = _("Public transport updated successfully.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["time_formset"] = (
            PublicTransportFormSet(self.request.POST, instance=self.object)
            if self.request.POST else PublicTransportFormSet(instance=self.object)
        )
        return context

    def get_form(self, form_class=None):
        return _apply_transport_type_logic(super().get_form(form_class), self.request, self.object)

    def form_valid(self, form):
        context = self.get_context_data()
        time_formset = context["time_formset"]
        if time_formset.is_valid():
            existing = sum(1 for f in time_formset if f.instance.pk and not f.cleaned_data.get("DELETE", False))
            new      = sum(1 for f in time_formset if f.cleaned_data.get("time") and not f.instance.pk)
            if existing + new < 1:
                form.add_error(None, _("Please keep or add at least one departure time."))
                return self.form_invalid(form)
            self.object = form.save()
            time_formset.instance = self.object
            time_formset.save()
            return super().form_valid(form)
        return self.form_invalid(form)

    def test_func(self):
        return self.request.user.is_staff


class PublicTransportDeleteView(UserPassesTestMixin, LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = PublicTransport
    success_url = reverse_lazy("guard:publicTransportsList")
    success_message = _("Public transport has been deleted.")

    def delete(self, request, *args, **kwargs):
        messages.warning(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)

    def test_func(self):
        return self.request.user.is_staff

# =============================================================================
# PARTNERS (AJOUT ISLEM — LegacyPartner + email verification)
# =============================================================================

class PartnerListView(UserPassesTestMixin, LoginRequiredMixin, ListView):
    model = LegacyPartner
    template_name = "guard/views/partners/list.html"
    context_object_name = "partners"
    ordering = ["-id"]

    def test_func(self):
        return self.request.user.is_staff


class PartnerCreateView(UserPassesTestMixin, LoginRequiredMixin, CreateView):
    model = LegacyPartner
    form_class = PartnerForm
    template_name = 'guard/views/partners/index.html'
    success_url = reverse_lazy('guard:partnersList')

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from cities_light.models import City
        context['cities'] = City.objects.all().values('id', 'name').order_by('name')
        context['categories'] = LocationCategory.objects.all().order_by('name')
        return context

    def form_valid(self, form):
        self.object = form.save()

        # Generate or get password
        plain_password = form.cleaned_data.get('password') or ''.join(
            secrets.choice(string.ascii_letters + string.digits) for _ in range(10)
        )
        
        # Create user account for the partner if it doesn't exist
        if not self.object.user:
            # Base username on name, fall back to email
            base_username = self.object.name.replace(' ', '_').lower()
            if not base_username:
                base_username = self.object.email.split('@')[0]
            
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            user = User.objects.create_user(
                username=username,
                email=self.object.email,
                password=plain_password,
                is_active=False,
            )
            self.object.user = user
            self.object.save()
            
            # Ensure UserProfile has the correct type
            UserProfile.objects.update_or_create(
                user=user,
                defaults={"user_type": UserProfile.UserType.CLIENT_PARTNER},
            )

            # --- AJOUT : Création automatique dans le nouveau module Partners ---
            if PartnerAccount:
                try:
                    # On cherche si un partenaire avec cet email existe déjà
                    existing_p = PartnerAccount.objects.filter(email=self.object.email).first()
                    if existing_p:
                        if not existing_p.user:
                            # Si le partenaire existe mais n'a pas d'utilisateur, on le lie
                            existing_p.user = user
                            existing_p.company_name = self.object.name
                            existing_p.save()
                        else:
                            # Si l'email est déjà pris par un AUTRE partenaire avec utilisateur
                            # On crée un nouveau profil avec un email légèrement différent pour éviter le crash unique
                            from uuid import uuid4
                            unique_email = f"{uuid4().hex[:5]}_{self.object.email}"
                            PartnerAccount.objects.create(
                                user=user,
                                company_name=self.object.name,
                                email=unique_email,
                                is_active=True,
                                is_verified=False
                            )
                    else:
                        # Création normale
                        PartnerAccount.objects.create(
                            user=user,
                            company_name=self.object.name,
                            email=self.object.email,
                            is_active=True,
                            is_verified=False
                        )
                except Exception as e:
                    logger.error(f"Erreur création profil partenaire (nouveau module): {e}")
            # -------------------------------------------------------------------

        if send_validation_email:
            current_lang = get_language()
            try:
                success = send_validation_email(
                    self.object,
                    plain_password=plain_password,
                    lang=current_lang
                )
                if not success:
                    messages.warning(self.request, _("Partner created, but validation email could not be sent. Please check your SMTP settings."))
            except Exception as e:
                logger.error(f"Erreur envoi email partenaire: {e}")
                messages.error(self.request, _("An error occurred while sending the validation email."))

        selected_locations = list(form.cleaned_data.get('locations') or [])
        
        # Handle custom location
        custom_name = form.cleaned_data.get('custom_location')
        custom_city = form.cleaned_data.get('custom_city')
        if custom_name and custom_city:
            new_loc = Location.objects.create(
                name=custom_name,
                city=custom_city,
                latitude=0.0, # Default or set from city
                longitude=0.0,
                story=f"Added by partner: {self.object.name}"
            )
            selected_locations.append(new_loc)

        self.object.locations.clear()
        if selected_locations:
            self.object.locations.set(selected_locations)

        messages.success(self.request, _("Partner created successfully."))
        return HttpResponseRedirect(self.get_success_url())


class PartnerUpdateView(UserPassesTestMixin, LoginRequiredMixin, UpdateView):
    model = LegacyPartner
    form_class = PartnerForm
    template_name = "guard/views/partners/index.html"
    success_url = reverse_lazy("guard:partnersList")

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from cities_light.models import City
        context['cities'] = City.objects.all().values('id', 'name').order_by('name')
        context['categories'] = LocationCategory.objects.all().order_by('name')
        return context

    def form_valid(self, form):
        self.object = form.save()

        selected_locations = list(form.cleaned_data.get('locations') or [])

        # Handle custom location
        custom_name = form.cleaned_data.get('custom_location')
        custom_city = form.cleaned_data.get('custom_city')
        if custom_name and custom_city:
            new_loc = Location.objects.create(
                name=custom_name,
                city=custom_city,
                latitude=0.0,
                longitude=0.0,
                story=f"Added by partner: {self.object.name}"
            )
            selected_locations.append(new_loc)

        self.object.locations.clear()
        if selected_locations:
            self.object.locations.set(selected_locations)

        messages.success(self.request, _("Partner updated successfully."))
        return HttpResponseRedirect(self.get_success_url())


class PartnerDeleteView(UserPassesTestMixin, LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = LegacyPartner
    template_name = "guard/views/partners/delete.html"
    success_url = reverse_lazy("guard:partnersList")
    success_message = _("Partner deleted successfully.")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)

    def test_func(self):
        return self.request.user.is_staff


def verify_partner_email(request):
    """Vue appelée quand le partenaire clique sur le lien de vérification email."""
    token = request.GET.get('token')
    if not token:
        return HttpResponse("Token manquant", status=400)
    try:
        data = signing.loads(token, max_age=172800)  # 48h
        partner_id = data.get('partner_id')
        partner = LegacyPartner.objects.get(id=partner_id)
        if not partner.is_verified:
            partner.is_verified = True
            # Activate the user account
            if partner.user:
                partner.user.is_active = True
                partner.user.save()
                # Mark the new Partner model as verified too
                if PartnerAccount:
                    PartnerAccount.objects.filter(user=partner.user).update(is_verified=True)
            partner.save()
            return render(request, 'verification_success.html', {'name': partner.name})
        else:
            return HttpResponse("Compte déjà vérifié.")
    except (signing.SignatureExpired, signing.BadSignature):
        return HttpResponse("Le lien est invalide ou a expiré.", status=400)

# =============================================================================
# SPONSORS (AJOUT ISLEM — now with UserPassesTestMixin)
# =============================================================================

class SponsorListView(UserPassesTestMixin, LoginRequiredMixin, ListView):
    model = Sponsor
    template_name = "guard/views/sponsors/list.html"
    context_object_name = "sponsors"
    ordering = ["-id"]
    def test_func(self): return self.request.user.is_staff


class SponsorCreateView(UserPassesTestMixin, LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Sponsor
    form_class = SponsorForm
    template_name = "guard/views/sponsors/index.html"
    success_url = reverse_lazy("guard:sponsorsList")
    success_message = _("Sponsor created successfully.")
    def test_func(self): return self.request.user.is_staff


class SponsorUpdateView(UserPassesTestMixin, LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Sponsor
    form_class = SponsorForm
    template_name = "guard/views/sponsors/index.html"
    success_url = reverse_lazy("guard:sponsorsList")
    success_message = _("Sponsor updated successfully.")
    def test_func(self): return self.request.user.is_staff


class SponsorDeleteView(UserPassesTestMixin, LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Sponsor
    template_name = "guard/views/sponsors/delete.html"
    success_url = reverse_lazy("guard:sponsorsList")
    success_message = _("Sponsor deleted successfully.")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)

    def test_func(self): return self.request.user.is_staff

# ── TRACKING (original click-redirect views) ──────────────────────────────────

class AdTrackingView(View):
    def get(self, request, pk):
        ad = get_object_or_404(Ad, pk=pk)
        return HttpResponseRedirect(ad.destination_link) if ad.destination_link else redirect('guard:adsList')

class EventTrackingView(View):
    def get(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        return HttpResponseRedirect(event.link) if event.link else redirect('guard:eventsList')

class EventClickView(EventTrackingView): pass
class AdClickView(AdTrackingView): pass

# ── SUBSCRIBERS ───────────────────────────────────────────────────────────────

class SubscribersListView(StaffRequiredMixin, LoginRequiredMixin, ListView):
    model = UserProfile
    template_name = "guard/views/subscribers/list.html"
    context_object_name = "subscribers"

@login_required
def check_user_type(request):
    if request.user.is_staff:
        return redirect('guard:dashboard')
    return redirect('/')

# ── PRICING SETTINGS ──────────────────────────────────────────────────────────

from shared.models import PricingSettings

class PricingSettingsView(StaffRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "guard/views/pricing_settings.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pricing"] = PricingSettings.get()
        return context

    def post(self, request, *args, **kwargs):
        pricing = PricingSettings.get()
        boost = request.POST.get("boost_price_per_day")
        ad    = request.POST.get("ad_price_per_day")
        if boost:
            pricing.boost_price_per_day = boost
        if ad:
            pricing.ad_price_per_day = ad
        pricing.updated_by = request.user
        pricing.save()
        messages.success(request, "Prix mis à jour avec succès.")
        return redirect(request.path)

# ── RECEIPTS ──────────────────────────────────────────────────────────────────

from partners.models import ReceiptHistory

class ReceiptListView(StaffRequiredMixin, LoginRequiredMixin, ListView):
    model               = ReceiptHistory
    template_name       = "guard/views/receipts/list.html"
    context_object_name = "receipts"
    ordering            = ['-created_at']
    paginate_by         = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related('partner')
        q  = self.request.GET.get('q', '').strip()
        pt = self.request.GET.get('payment_type', '').strip()
        if q:
            qs = qs.filter(
                models.Q(receipt_number__icontains=q) |
                models.Q(sent_to_email__icontains=q)  |
                models.Q(partner__company_name__icontains=q)
            )
        if pt:
            qs = qs.filter(payment_type=pt)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q']            = self.request.GET.get('q', '')
        context['payment_type'] = self.request.GET.get('payment_type', '')
        return context

# ── EMAIL CHANGE REQUESTS ─────────────────────────────────────────────────────

class EmailChangeListView(StaffRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "guard/views/partners/email_changes.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if PartnerAccount:
            context['pending'] = PartnerAccount.objects.filter(
                pending_email__isnull=False
            ).exclude(pending_email='').order_by('-created_at')
        return context

    def post(self, request, *args, **kwargs):
        partner_id = request.POST.get('partner_id')
        action     = request.POST.get('action')

        partner = get_object_or_404(PartnerAccount, id=partner_id)

        if action == 'approve' and partner.pending_email:
            old_email             = partner.email
            new_email             = partner.pending_email
            partner.email         = new_email
            partner.pending_email = None
            partner.save(update_fields=['email', 'pending_email'])

            if partner.user:
                partner.user.email    = new_email
                partner.user.username = new_email
                partner.user.save()

            messages.success(request, f"Email de {partner.company_name} mis à jour : {old_email} → {new_email}")

        elif action == 'reject':
            partner.pending_email = None
            partner.save(update_fields=['pending_email'])
            messages.warning(request, f"Demande de changement d'email de {partner.company_name} rejetée.")

        return redirect('guard:email_changes')
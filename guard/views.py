from django.http import HttpResponseRedirect, Http404
from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import (
    CreateView, UpdateView, DeleteView,
    ListView, TemplateView, DetailView,
)
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.http import JsonResponse
from django.core.cache import cache
from django.shortcuts import redirect, get_object_or_404
from django.views import View
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from shared.models import UserProfile
from shared.short_io import ShortIOService

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
    LocationCategory, Location,
    Event, UserProfile, Tip,
    Hiking, Ad,
    PublicTransport, PublicTransportType,
    Partner, Sponsor,
)


# ══════════════════════════════════════════════════════════════════
#   DASHBOARD
# ══════════════════════════════════════════════════════════════════

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "guard/views/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        from django.utils import timezone
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        context["db_stats"] = {
            "total_locations":      Location.objects.count(),
            "locations_this_month": Location.objects.filter(created_at__gte=month_start).count(),
            "total_events":         Event.objects.count(),
            "upcoming_events":      Event.objects.filter(startDate__gte=now.date()).count(),
            "total_hikings":        Hiking.objects.count(),
            "total_ads":            Ad.objects.count(),
            "active_ads":           Ad.objects.filter(is_active=True).count(),
        }

        cache_key = f"dashboard_analytics_stats_{self.request.user.id}"
        stats = cache.get(cache_key)

        if not stats:
            service = ShortIOService()
            profile = self.request.user.profile
            ad_ids = list(
                Ad.objects.filter(
                    client=profile, is_active=True, short_id__isnull=False
                ).values_list("short_id", flat=True)
            )
            event_ids = list(
                Event.objects.filter(
                    client=profile, short_id__isnull=False
                ).values_list("short_id", flat=True)
            )
            period = "week"
            ads_stats = service.get_aggregated_link_statistics(ad_ids, period) or {
                "totalClicks": 0, "clickStatistics": {"timeline": []},
            }
            events_stats = service.get_aggregated_link_statistics(event_ids, period) or {
                "totalClicks": 0, "clickStatistics": {"timeline": []},
            }
            stats = {"ads": ads_stats, "events": events_stats}
            cache.set(cache_key, stats, 60 * 15)

        context["stats"] = stats
        return context


# ══════════════════════════════════════════════════════════════════
#   SUBSCRIBERS
# ══════════════════════════════════════════════════════════════════

class SubscribersListView(UserPassesTestMixin, LoginRequiredMixin, ListView):
    model = UserProfile
    template_name = "guard/views/subscribers/list.html"
    context_object_name = "subscribers"
    ordering = ["-id"]

    def test_func(self):
        return self.request.user.is_staff


# ══════════════════════════════════════════════════════════════════
#   LOCATIONS
# ══════════════════════════════════════════════════════════════════

class LocationsListView(UserPassesTestMixin, LoginRequiredMixin, ListView):
    model = Location
    template_name = "guard/views/locations/list.html"
    context_object_name = "locations"
    ordering = ["-created_at"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["location_categories"] = LocationCategory.objects.all()
        return context

    def test_func(self):
        return self.request.user.is_staff


class LocationCreateView(UserPassesTestMixin, LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Location
    template_name = "guard/views/locations/index.html"
    form_class = LocationForm
    success_url = reverse_lazy("guard:locationsList")
    success_message = _("Location created successfully.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["image_formset"] = ImageLocationFormSet(self.request.POST, self.request.FILES)
        else:
            context["image_formset"] = ImageLocationFormSet()
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
                form.add_error(None, _("Please upload at least one image."))
                return self.form_invalid(form)
            self.object = form.save()
            image_formset.instance = self.object
            image_formset.save()
            return super().form_valid(form)
        return self.form_invalid(form)

    def test_func(self):
        return self.request.user.is_staff


class LocationUpdateView(UserPassesTestMixin, LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Location
    template_name = "guard/views/locations/index.html"
    form_class = LocationForm
    success_url = reverse_lazy("guard:locationsList")
    success_message = _("Location updated successfully.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["image_formset"] = ImageLocationFormSet(self.request.POST, self.request.FILES, instance=self.object)
        else:
            context["image_formset"] = ImageLocationFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        image_formset = context["image_formset"]
        if image_formset.is_valid():
            existing = sum(1 for f in image_formset if f.instance.pk and not f.cleaned_data.get("DELETE", False))
            new = sum(1 for f in image_formset if f.cleaned_data.get("image") and not f.instance.pk)
            if existing + new < 1:
                form.add_error(None, _("Veuillez conserver ou télécharger au moins une image."))
                return self.form_invalid(form)
            self.object = form.save()
            image_formset.instance = self.object
            image_formset.save()
            return super().form_valid(form)
        return self.form_invalid(form)

    def test_func(self):
        return self.request.user.is_staff


class LocationDeleteView(UserPassesTestMixin, LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Location
    success_url = reverse_lazy("guard:locationsList")
    success_message = _("Unfortunately, this location has been deleted")

    def delete(self, request, *args, **kwargs):
        messages.warning(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)

    def test_func(self):
        return self.request.user.is_staff


# ══════════════════════════════════════════════════════════════════
#   PUBLIC TRANSPORT
# ══════════════════════════════════════════════════════════════════

class PublicTransportListView(UserPassesTestMixin, LoginRequiredMixin, ListView):
    model = PublicTransport
    template_name = "guard/views/publicTransports/list.html"
    context_object_name = "transports"
    ordering = ["-created_at"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["transport_types"] = PublicTransportType.objects.all()
        return context

    def get_queryset(self):
        return (
            super().get_queryset()
            .prefetch_related("publicTransportTimes")
            .select_related("publicTransportType", "city", "fromRegion", "toRegion")
        )

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
        if self.request.POST:
            context["time_formset"] = PublicTransportFormSet(self.request.POST)
        else:
            context["time_formset"] = PublicTransportFormSet()
        return context

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
        if self.request.POST:
            context["time_formset"] = PublicTransportFormSet(self.request.POST, instance=self.object)
        else:
            context["time_formset"] = PublicTransportFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        time_formset = context["time_formset"]
        if time_formset.is_valid():
            existing = sum(1 for f in time_formset if f.instance.pk and not f.cleaned_data.get("DELETE", False))
            new = sum(1 for f in time_formset if f.cleaned_data.get("time") and not f.instance.pk)
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

    def get(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        messages.warning(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)

    def test_func(self):
        return self.request.user.is_staff


# ══════════════════════════════════════════════════════════════════
#   EVENTS
# ══════════════════════════════════════════════════════════════════

class EventListView(LoginRequiredMixin, ListView):
    model = Event
    template_name = "guard/views/events/list.html"
    context_object_name = "events"
    ordering = ["-created_at"]

    def get_queryset(self):
        return super().get_queryset().filter(client=self.request.user.profile)


class EventCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
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
        if self.request.POST:
            context["image_formset"] = ImageEventFormSet(self.request.POST, self.request.FILES)
        else:
            context["image_formset"] = ImageEventFormSet()
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
            try:
                service = ShortIOService()
                short_data = service.shorten_url(self.object.link, title="Event Campaign")
                if short_data:
                    self.object.short_link = short_data.get("secureShortURL") or short_data.get("shortURL")
                    self.object.short_id = short_data.get("idString")
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Short.io error: {e}")
            self.object.save()
            image_formset.instance = self.object
            image_formset.save()
            messages.success(self.request, self.success_message)
            return HttpResponseRedirect(self.get_success_url())
        return self.form_invalid(form)


class EventUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
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
        if self.request.POST:
            context["image_formset"] = ImageEventFormSet(self.request.POST, self.request.FILES, instance=self.object)
        else:
            context["image_formset"] = ImageEventFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        image_formset = context["image_formset"]
        if image_formset.is_valid():
            existing = sum(1 for f in image_formset if f.instance.pk and not f.cleaned_data.get("DELETE", False))
            new = sum(1 for f in image_formset if f.cleaned_data.get("image") and not f.instance.pk)
            if existing + new < 1:
                form.add_error(None, _("Veuillez conserver ou télécharger au moins une image."))
                return self.form_invalid(form)
            self.object = form.save(commit=False)
            if "link" in form.changed_data:
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
                            self.object.short_id = short_data.get("idString")
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Short.io error: {e}")
            self.object.save()
            image_formset.instance = self.object
            image_formset.save()
            messages.success(self.request, self.success_message)
            return HttpResponseRedirect(self.get_success_url())
        return self.form_invalid(form)


class EventTrackingView(LoginRequiredMixin, DetailView):
    model = Event
    template_name = "guard/views/events/partials/tracking.html"
    context_object_name = "object"

    def get_queryset(self):
        return super().get_queryset().filter(client=self.request.user.profile)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        period = self.request.GET.get("period", "today")
        context["period"] = period
        context["page_title"] = self.object.name
        if self.object.short_id:
            service = ShortIOService()
            context["stats"] = service.get_link_statistics(self.object.short_id, period)
        return context


class EventDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Event
    success_url = reverse_lazy("guard:eventsList")
    success_message = _("Unfortunately, this event has been deleted")

    def get_queryset(self):
        return super().get_queryset().filter(client=self.request.user.profile)

    def delete(self, request, *args, **kwargs):
        messages.warning(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)


# ══════════════════════════════════════════════════════════════════
#   TIPS
# ══════════════════════════════════════════════════════════════════

class TipsListView(UserPassesTestMixin, LoginRequiredMixin, ListView):
    model = Tip
    template_name = "guard/views/tips/list.html"
    context_object_name = "tips"
    ordering = ["-created_at"]

    def test_func(self):
        return self.request.user.is_staff


class TipCreateView(UserPassesTestMixin, LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Tip
    form_class = TipForm
    template_name = "guard/views/tips/index.html"
    success_url = reverse_lazy("guard:tipsList")
    success_message = _("Tip created successfully")

    def form_invalid(self, form):
        messages.error(self.request, _("Error creating tip. Please check the form."))
        return super().form_invalid(form)

    def test_func(self):
        return self.request.user.is_staff


class TipUpdateView(UserPassesTestMixin, LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Tip
    form_class = TipForm
    template_name = "guard/views/tips/index.html"
    success_url = reverse_lazy("guard:tipsList")
    success_message = _("Tip updated successfully")

    def form_invalid(self, form):
        messages.error(self.request, _("Error updating tip. Please check the form."))
        return super().form_invalid(form)

    def test_func(self):
        return self.request.user.is_staff


class TipDeleteView(UserPassesTestMixin, LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Tip
    success_url = reverse_lazy("guard:tipsList")
    success_message = _("Tip deleted successfully")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)

    def test_func(self):
        return self.request.user.is_staff


# ══════════════════════════════════════════════════════════════════
#   HIKING
# ══════════════════════════════════════════════════════════════════

class HikingListView(UserPassesTestMixin, LoginRequiredMixin, ListView):
    model = Hiking
    template_name = "guard/views/hiking/list.html"
    context_object_name = "hikings"
    ordering = ["-created_at"]

    def test_func(self):
        return self.request.user.is_staff


class HikingCreateView(UserPassesTestMixin, LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Hiking
    form_class = HikingForm
    template_name = "guard/views/hiking/index.html"
    success_url = reverse_lazy("guard:hikingsList")
    success_message = _("Hiking created successfully")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["image_formset"] = ImageHikingFormSet(self.request.POST, self.request.FILES)
            context["location_formset"] = HikingLocationFormSet(self.request.POST)
        else:
            context["image_formset"] = ImageHikingFormSet()
            context["location_formset"] = HikingLocationFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        image_formset = context["image_formset"]
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
            image_formset.instance = self.object
            image_formset.save()
            location_formset.instance = self.object
            location_formset.save()
            return super().form_valid(form)
        return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("Error creating hiking. Please check the form."))
        return super().form_invalid(form)

    def test_func(self):
        return self.request.user.is_staff


class HikingUpdateView(UserPassesTestMixin, LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Hiking
    form_class = HikingForm
    template_name = "guard/views/hiking/index.html"
    success_url = reverse_lazy("guard:hikingsList")
    success_message = _("Hiking updated successfully")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["image_formset"] = ImageHikingFormSet(self.request.POST, self.request.FILES, instance=self.object)
            context["location_formset"] = HikingLocationFormSet(self.request.POST, instance=self.object)
        else:
            context["image_formset"] = ImageHikingFormSet(instance=self.object)
            context["location_formset"] = HikingLocationFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        image_formset = context["image_formset"]
        location_formset = context["location_formset"]
        if image_formset.is_valid() and location_formset.is_valid():
            existing = sum(1 for f in image_formset if f.instance.pk and not f.cleaned_data.get("DELETE", False))
            new = sum(1 for f in image_formset if f.cleaned_data.get("image") and not f.instance.pk)
            if existing + new < 1:
                form.add_error(None, _("Veuillez conserver ou télécharger au moins une image."))
                return self.form_invalid(form)
            self.object = form.save()
            image_formset.instance = self.object
            image_formset.save()
            location_formset.instance = self.object
            location_formset.save()
            return super().form_valid(form)
        return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("Error updating hiking. Please check the form."))
        return super().form_invalid(form)

    def test_func(self):
        return self.request.user.is_staff


class HikingDeleteView(UserPassesTestMixin, LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Hiking
    success_url = reverse_lazy("guard:hikingsList")
    success_message = _("Hiking deleted successfully")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)

    def test_func(self):
        return self.request.user.is_staff


# ══════════════════════════════════════════════════════════════════
#   ADS
# ══════════════════════════════════════════════════════════════════

class AdListView(LoginRequiredMixin, ListView):
    model = Ad
    template_name = "guard/views/ads/list.html"
    context_object_name = "ads"
    ordering = ["-created_at"]

    def get_queryset(self):
        return super().get_queryset().filter(client=self.request.user.profile)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = ShortIOService()
        for ad in context["ads"]:
            if ad.short_id:
                try:
                    clicks = service.get_clicks(ad.short_id)
                    if clicks != ad.clicks:
                        ad.clicks = clicks
                        ad.save(update_fields=["clicks"])
                except Exception:
                    pass
        return context


class AdCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Ad
    form_class = AdForm
    template_name = "guard/views/ads/index.html"
    success_url = reverse_lazy("guard:adsList")
    success_message = _("Ad created successfully")

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.client = self.request.user.profile
        try:
            service = ShortIOService()
            short_data = service.shorten_url(self.object.link, title="Ad Campaign")
            if short_data:
                self.object.short_link = short_data.get("secureShortURL") or short_data.get("shortURL")
                self.object.short_id = short_data.get("idString")
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Short.io error: {e}")
        self.object.save()
        messages.success(self.request, self.success_message)
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        messages.error(self.request, _("Error creating ad. Please check the form."))
        return super().form_invalid(form)


class AdUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Ad
    form_class = AdForm
    template_name = "guard/views/ads/index.html"
    success_url = reverse_lazy("guard:adsList")
    success_message = _("Ad updated successfully")

    def get_queryset(self):
        return super().get_queryset().filter(client=self.request.user.profile)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        if "link" in form.changed_data:
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
                        self.object.short_id = short_data.get("idString")
                        self.object.clicks = 0
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Short.io error: {e}")
        self.object.save()
        messages.success(self.request, self.success_message)
        return HttpResponseRedirect(self.get_success_url())


class AdTrackingView(LoginRequiredMixin, DetailView):
    model = Ad
    template_name = "guard/views/ads/partials/tracking.html"
    context_object_name = "object"

    def get_queryset(self):
        return super().get_queryset().filter(client=self.request.user.profile)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        period = self.request.GET.get("period", "today")
        context["period"] = period
        context["page_title"] = self.object.link
        if self.object.short_id:
            service = ShortIOService()
            context["stats"] = service.get_link_statistics(self.object.short_id, period)
        return context


class AdDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Ad
    success_url = reverse_lazy("guard:adsList")
    success_message = _("Ad deleted successfully")

    def get_queryset(self):
        return super().get_queryset().filter(client=self.request.user.profile)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)


# ══════════════════════════════════════════════════════════════════
#   PARTNERS
# ══════════════════════════════════════════════════════════════════

class PartnerListView(UserPassesTestMixin, LoginRequiredMixin, ListView):
    model = Partner
    template_name = "guard/views/partners/list.html"
    context_object_name = "partners"
    ordering = ["-id"]

    def test_func(self):
        return self.request.user.is_staff


class PartnerCreateView(UserPassesTestMixin, LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Partner
    form_class = PartnerForm
    template_name = "guard/views/partners/index.html"
    success_url = reverse_lazy("guard:partnersList")
    success_message = _("Partner created successfully.")

    def test_func(self):
        return self.request.user.is_staff


class PartnerUpdateView(UserPassesTestMixin, LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Partner
    form_class = PartnerForm
    template_name = "guard/views/partners/index.html"
    success_url = reverse_lazy("guard:partnersList")
    success_message = _("Partner updated successfully.")

    def test_func(self):
        return self.request.user.is_staff


class PartnerDeleteView(UserPassesTestMixin, LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Partner
    template_name = "guard/views/partners/delete.html"
    success_url = reverse_lazy("guard:partnersList")
    success_message = _("Partner deleted successfully.")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)

    def test_func(self):
        return self.request.user.is_staff


# ══════════════════════════════════════════════════════════════════
#   SPONSORS
# ══════════════════════════════════════════════════════════════════

class SponsorListView(UserPassesTestMixin, LoginRequiredMixin, ListView):
    model = Sponsor
    template_name = "guard/views/sponsors/list.html"
    context_object_name = "sponsors"
    ordering = ["-id"]

    def test_func(self):
        return self.request.user.is_staff


class SponsorCreateView(UserPassesTestMixin, LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Sponsor
    form_class = SponsorForm
    template_name = "guard/views/sponsors/index.html"
    success_url = reverse_lazy("guard:sponsorsList")
    success_message = _("Sponsor created successfully.")

    def test_func(self):
        return self.request.user.is_staff


class SponsorUpdateView(UserPassesTestMixin, LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Sponsor
    form_class = SponsorForm
    template_name = "guard/views/sponsors/index.html"
    success_url = reverse_lazy("guard:sponsorsList")
    success_message = _("Sponsor updated successfully.")

    def test_func(self):
        return self.request.user.is_staff


class SponsorDeleteView(UserPassesTestMixin, LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Sponsor
    template_name = "guard/views/sponsors/delete.html"
    success_url = reverse_lazy("guard:sponsorsList")
    success_message = _("Sponsor deleted successfully.")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)

    def test_func(self):
        return self.request.user.is_staff


# ══════════════════════════════════════════════════════════════════
#   API ENDPOINTS
# ══════════════════════════════════════════════════════════════════

@login_required
def get_cities_by_country(request, country_id):
    from cities_light.models import City
    cities = City.objects.filter(country_id=country_id).values("id", "name")
    return JsonResponse({"success": True, "cities": list(cities)})


@login_required
def get_subregions_by_city(request, city_id):
    from cities_light.models import City, SubRegion
    cache_key = f"subregions_city_{city_id}"
    result = cache.get(cache_key)
    if result is None:
        try:
            city = City.objects.select_related("region").get(id=city_id)
            subregions = list(
                SubRegion.objects.filter(region=city.region)
                .order_by("name").values("id", "name")
            )
            result = {"success": True, "subregions": subregions}
            cache.set(cache_key, result, 60 * 5)
        except City.DoesNotExist:
            return JsonResponse({"success": False, "error": "City not found"}, status=404)
    return JsonResponse(result)


@login_required
def get_locations_by_city(request, city_id):
    try:
        locations = Location.objects.filter(city_id=city_id).values("id", "name_en", "name_fr")
        return JsonResponse({"success": True, "locations": list(locations)})
    except Exception:
        return JsonResponse({"success": False, "error": "Error fetching locations"}, status=500)


@login_required
def get_all_subregions(request):
    from cities_light.models import SubRegion
    subregions = SubRegion.objects.all().order_by("name").values("id", "name")
    return JsonResponse({"success": True, "subregions": list(subregions)})


@login_required
def get_schedules(request):
    from guard.models import PublicTransport
    type_id = request.GET.get("type")
    from_id = request.GET.get("from")
    to_id   = request.GET.get("to")
    if not all([type_id, from_id, to_id]):
        return JsonResponse({"success": False, "error": "Missing parameters"}, status=400)

    schedules = []
    for direction, f, t in [("aller", from_id, to_id), ("retour", to_id, from_id)]:
        routes = PublicTransport.objects.filter(
            publicTransportType_id=type_id, fromRegion_id=f, toRegion_id=t,
        ).select_related("fromRegion", "toRegion").prefetch_related("publicTransportTimes")
        for route in routes:
            times = [ti.time.strftime("%H:%M") for ti in route.publicTransportTimes.all().order_by("time")]
            if times:
                schedules.append({
                    "line": route.busNumber or "N/A",
                    "from": route.fromRegion.name if route.fromRegion else "?",
                    "to": route.toRegion.name if route.toRegion else "?",
                    "times": times,
                    "direction": direction,
                })
    return JsonResponse({"success": True, "schedules": schedules})


# ══════════════════════════════════════════════════════════════════
#   CLICK TRACKING TEMPS RÉEL
# ══════════════════════════════════════════════════════════════════

class AdClickView(View):
    """
    URL: /ad/<int:pk>/go/
    Enregistre le clic, met l'Ad Active, redirige vers le vrai lien.
    """
    def get(self, request, pk):
        ad = get_object_or_404(Ad, pk=pk)
        if not ad.link:
            raise Http404

        # 1. Enregistrer le clic
        from .models import ClickLog
        ClickLog.objects.create(
            content_type='ad',
            object_id=pk,
            short_id=ad.short_id or '',
            ip_address=self._get_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:300],
        )

        # 2. ✅ Marquer Active + mettre à jour last_clicked_at
        from django.utils import timezone
        ad.is_active = True
        ad.last_clicked_at = timezone.now()
        ad.save(update_fields=['is_active', 'last_clicked_at'])

        # 3. Broadcaster via WebSocket
        self._broadcast('ad')

        return HttpResponseRedirect(ad.link)

    @staticmethod
    def _get_ip(request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        return xff.split(',')[0] if xff else request.META.get('REMOTE_ADDR')

    @staticmethod
    def _broadcast(content_type):
        from .models import ClickLog
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models import Count
        from django.db.models.functions import TruncDate

        now   = timezone.now()
        start = now - timedelta(days=6)

        def series(ct):
            counts = {
                str(r['day']): r['n']
                for r in ClickLog.objects
                    .filter(content_type=ct, clicked_at__gte=start)
                    .annotate(day=TruncDate('clicked_at'))
                    .values('day')
                    .annotate(n=Count('id'))
            }
            result = []
            for i in range(6, -1, -1):
                d = (now - timedelta(days=i)).date()
                result.append(counts.get(str(d), 0))
            return result

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "dashboard_realtime",
            {
                "type":          "click_update",
                "content_type":  content_type,
                "total_ads":     ClickLog.objects.filter(content_type='ad').count(),
                "total_events":  ClickLog.objects.filter(content_type='event').count(),
                "ads_series":    series('ad'),
                "events_series": series('event'),
            }
        )


class EventClickView(AdClickView):
    """
    URL: /event/<int:pk>/go/
    """
    def get(self, request, pk):
        from .models import Event as EventModel
        event = get_object_or_404(EventModel, pk=pk)
        if not event.link:
            raise Http404

        from .models import ClickLog
        ClickLog.objects.create(
            content_type='event',
            object_id=pk,
            short_id=event.short_id or '',
            ip_address=self._get_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:300],
        )

        self._broadcast('event')
        return HttpResponseRedirect(event.link)
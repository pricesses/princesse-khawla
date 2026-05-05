from django.urls import path, include

from .views import (
    DashboardView,
    SubscribersListView,
    LocationsListView,
    LocationCreateView,
    LocationUpdateView,
    LocationDeleteView,

    # ── Staff Event views (your originals) ──────────────────────────
    EventListView,
    EventCreateView,
    EventUpdateView,
    EventDeleteView,
    EventTrackingView,
    EventClickView,
    # ── Partner-facing Event views (AJOUT ISLEM) ─────────────────────
    PartnerEventListView,
    PartnerEventCreateView,
    PartnerEventUpdateView,
    PartnerEventDeleteView,
    PartnerEventTrackingView,
    # ── Tips ─────────────────────────────────────────────────────────
    TipsListView,
    TipCreateView,
    TipUpdateView,
    TipDeleteView,
    # ── Hiking ───────────────────────────────────────────────────────
    HikingListView,
    HikingCreateView,
    HikingUpdateView,
    HikingDeleteView,
    # ── Staff Ad views (your originals) ──────────────────────────────
    AdListView,
    AdCreateView,
    AdUpdateView,
    AdDeleteView,
    AdTrackingView,
    AdClickView,
    # ── Partner-facing Ad views (AJOUT ISLEM) ────────────────────────
    PartnerAdListView,
    PartnerAdCreateView,
    PartnerAdUpdateView,
    PartnerAdDeleteView,
    PartnerAdTrackingView,
    AdsDashboardView,
    CreateCheckoutSessionView,
    StripeWebhookView,
    AdConfirmPaymentView,
    # ── Public Transport ─────────────────────────────────────────────
    PublicTransportListView,
    PublicTransportCreateView,
    PublicTransportUpdateView,
    PublicTransportDeleteView,
    # ── Partners ─────────────────────────────────────────────────────
    PartnerListView,
    PartnerCreateView,
    PartnerUpdateView,
    PartnerDeleteView,
    # ── Sponsors ─────────────────────────────────────────────────────
    SponsorListView,
    SponsorCreateView,
    SponsorUpdateView,
    SponsorDeleteView,
    # ── API helpers ──────────────────────────────────────────────────
    get_cities_by_country,
    get_subregions_by_city,
    get_all_subregions,
    get_schedules,
    get_locations_by_city,
    # ── Other ────────────────────────────────────────────────────────
    PricingSettingsView,
    ReceiptListView,
    EmailChangeListView,
    verify_partner_email,

)

app_name = "guard"

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),

    # ── Staff-only area ──────────────────────────────────────────────────────
    path(
        "staff/",
        include([
            path("subscribersList/", SubscribersListView.as_view(), name="subscribersList"),

            # Locations
            path("locationsList/", LocationsListView.as_view(), name="locationsList"),
            path("locations/create/", LocationCreateView.as_view(), name="location_create"),
            path("locations/update/<int:pk>/", LocationUpdateView.as_view(), name="location_update"),
            path("locations/delete/<int:pk>/", LocationDeleteView.as_view(), name="location_delete"),

            # Staff Events
            path("eventsList/", EventListView.as_view(), name="eventsList"),
            path("events/create/", EventCreateView.as_view(), name="event_create"),
            path("events/update/<int:pk>/", EventUpdateView.as_view(), name="event_update"),
            path("events/delete/<int:pk>/", EventDeleteView.as_view(), name="event_delete"),
            path("events/track/<int:pk>/", EventTrackingView.as_view(), name="event_track"),

            # Tips
            path("tips/", TipsListView.as_view(), name="tipsList"),
            path("tips/create/", TipCreateView.as_view(), name="tip_create"),
            path("tips/update/<int:pk>/", TipUpdateView.as_view(), name="tip_update"),
            path("tips/delete/<int:pk>/", TipDeleteView.as_view(), name="tip_delete"),

            # Hiking
            path("hikings/", HikingListView.as_view(), name="hikingsList"),
            path("hikings/create/", HikingCreateView.as_view(), name="hiking_create"),
            path("hikings/update/<int:pk>/", HikingUpdateView.as_view(), name="hiking_update"),
            path("hikings/delete/<int:pk>/", HikingDeleteView.as_view(), name="hiking_delete"),

            # Public Transport
            path("publicTransportsList/", PublicTransportListView.as_view(), name="publicTransportsList"),
            path("publicTransports/create/", PublicTransportCreateView.as_view(), name="publicTransport_create"),
            path("publicTransports/update/<int:pk>/", PublicTransportUpdateView.as_view(), name="publicTransport_update"),
            path("publicTransports/delete/<int:pk>/", PublicTransportDeleteView.as_view(), name="publicTransport_delete"),

            # Partners
            path("partners/", PartnerListView.as_view(), name="partnersList"),
            path("partners/create/", PartnerCreateView.as_view(), name="partner_create"),
            path("partners/update/<int:pk>/", PartnerUpdateView.as_view(), name="partner_update"),
            path("partners/delete/<int:pk>/", PartnerDeleteView.as_view(), name="partner_delete"),

            # Sponsors
            path("sponsors/", SponsorListView.as_view(), name="sponsorsList"),
            path("sponsors/create/", SponsorCreateView.as_view(), name="sponsor_create"),
            path("sponsors/update/<int:pk>/", SponsorUpdateView.as_view(), name="sponsor_update"),
            path("sponsors/delete/<int:pk>/", SponsorDeleteView.as_view(), name="sponsor_delete"),

            # Staff Ads
            path("adsList/", AdListView.as_view(), name="adsList"),
            path("ads/create/", AdCreateView.as_view(), name="ad_create"),
            path("ads/update/<int:pk>/", AdUpdateView.as_view(), name="ad_update"),
            path("ads/delete/<int:pk>/", AdDeleteView.as_view(), name="ad_delete"),

            # Receipts
            path("receipts/list/", ReceiptListView.as_view(), name="receipt_list"),

            # Pricing
            path("settings/pricing/", PricingSettingsView.as_view(), name="pricing_settings"),
        ]),
    ),

    # ── Click tracking ───────────────────────────────────────────────────────
    path("ad/<int:pk>/go/",    AdClickView.as_view(),    name="ad_click"),
    path("event/<int:pk>/go/", EventClickView.as_view(), name="event_click"),

    # ── Partner-facing Events (AJOUT ISLEM) ──────────────────────────────────
    path("partner/events/",                      PartnerEventListView.as_view(),    name="partner_events_list"),
    path("partner/events/create/",               PartnerEventCreateView.as_view(),  name="partner_event_create"),
    path("partner/events/update/<int:pk>/",      PartnerEventUpdateView.as_view(),  name="partner_event_update"),
    path("partner/events/delete/<int:pk>/",      PartnerEventDeleteView.as_view(),  name="partner_event_delete"),
    path("partner/events/track/<int:pk>/",       PartnerEventTrackingView.as_view(),name="partner_event_track"),

    # ── Partner-facing Ads (AJOUT ISLEM) ─────────────────────────────────────
    path("partner/ads/",                         PartnerAdListView.as_view(),       name="partner_ads_list"),
    path("partner/ads/create/",                  PartnerAdCreateView.as_view(),     name="partner_ad_create"),
    path("partner/ads/update/<int:pk>/",         PartnerAdUpdateView.as_view(),     name="partner_ad_update"),
    path("partner/ads/delete/<int:pk>/",         PartnerAdDeleteView.as_view(),     name="partner_ad_delete"),
    path("partner/ads/track/<int:pk>/",          PartnerAdTrackingView.as_view(),   name="partner_ad_track"),
    path("partner/ads/dashboard/",               AdsDashboardView.as_view(),        name="ads_dashboard"),

    # ── Konnect payment (AJOUT ISLEM) ────────────────────────────────────────
    path("ads/<int:pk>/checkout/",               CreateCheckoutSessionView.as_view(), name="ad_checkout"),
    path("ads/webhook/konnect/",                 StripeWebhookView.as_view(),          name="konnect_webhook"),
    path("ads/<int:pk>/confirm-payment/",        AdConfirmPaymentView.as_view(),       name="ad_confirm_payment"),

    # ── API helpers ──────────────────────────────────────────────────────────
    path("api/cities/<int:country_id>/",         get_cities_by_country,    name="get_cities_by_country"),
    path("api/subregions/all/",                  get_all_subregions,       name="all_subregions"),
    path("api/subregions/<int:city_id>/",        get_subregions_by_city,   name="get_subregions_by_city"),
    path("api/locations/<int:city_id>/",         get_locations_by_city,    name="get_locations_by_city"),
    path("api/schedules/",                       get_schedules,            name="get_schedules"),

    # ── Email change management ───────────────────────────────────────────────
    path("partners/email-changes/",              EmailChangeListView.as_view(),    name="email_changes"),
    path("partners/verify-email/",               verify_partner_email,             name="verify_partner_email"),

    

]
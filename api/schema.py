import strawberry
import strawberry_django
from strawberry import auto
from typing import List, Optional
import math
from django.db.models import Q
from django.utils import timezone
import datetime
import uuid
from django.conf import settings
from graphql.validation import NoSchemaIntrospectionCustomRule
from strawberry.extensions import AddValidationRules
import asyncio
from asgiref.sync import sync_to_async

from guard.models import (
    Location, LocationCategory, Hiking, HikingLocation,
    Event, EventCategory, Ad, Tip, PublicTransport,
    PublicTransportType, PublicTransportTime, ImageLocation,
    ImageHiking, ImageEvent, ImageAd, Partner, Sponsor, Weekday,
)
from cities_light.models import City, Country
from shared.models import Page, UserPreference

from partners.models import (
    Partner as PartnerAccount,
    PartnerEvent,
    PartnerEventMedia,
    PartnerAd,
)


# ═══════════════════════════════════════════════════════════════════════════════
# TYPES EXISTANTS (inchangés)
# ═══════════════════════════════════════════════════════════════════════════════

@strawberry.type
class ImageFieldType:
    @strawberry.field
    def url(self, info, root) -> str:
        if not root:
            return ""
        try:
            return info.context.request.build_absolute_uri(root.url)
        except Exception:
            return root.url

    @strawberry.field
    def name(self, root) -> str:
        return root.name if root else ""

    @strawberry.field
    def path(self, root) -> str:
        return root.path if root and hasattr(root, "path") else ""

    @strawberry.field
    def size(self, root) -> int:
        return root.size if root and hasattr(root, "size") else 0

    @strawberry.field
    def width(self, root) -> Optional[int]:
        try:
            return root.width if root and hasattr(root, "width") else None
        except Exception:
            return None

    @strawberry.field
    def height(self, root) -> Optional[int]:
        try:
            return root.height if root and hasattr(root, "height") else None
        except Exception:
            return None


@strawberry_django.type(Page)
class PageType:
    id: auto
    slug: auto
    slug_en: str
    slug_fr: str
    is_active: auto
    created_at: auto
    updated_at: auto
    title: auto
    title_en: str
    title_fr: str
    content: str
    content_en: str
    content_fr: str


@strawberry_django.type(Weekday)
class WeekdayType:
    id: auto
    day: auto


@strawberry_django.type(Partner)
class PartnerType:
    id: auto
    name: auto
    link: auto

    @strawberry.field
    def image(self, root) -> ImageFieldType:
        return root.image


@strawberry_django.type(Sponsor)
class SponsorType:
    id: auto
    name: auto
    link: auto

    @strawberry.field
    def image(self, root) -> ImageFieldType:
        return root.image


@strawberry_django.type(ImageLocation)
class ImageLocationType:
    id: auto
    created_at: auto

    @strawberry.field
    def image(self, root) -> ImageFieldType:
        return root.image

    @strawberry.field(name="imageMobile")
    def image_mobile(self, root) -> Optional[ImageFieldType]:
        return root.image_mobile


@strawberry_django.type(LocationCategory)
class LocationCategoryType:
    id: auto
    name: auto
    name_en: str
    name_fr: str
    created_at: auto
    updated_at: auto


@strawberry_django.type(Location)
class LocationType:
    id: auto
    created_at: auto
    name: auto
    name_en: str
    name_fr: str
    longitude: auto
    latitude: auto
    is_active_ads: auto
    story: str
    story_en: str
    story_fr: str
    open_from: auto = strawberry_django.field(field_name="openFrom")
    open_to: auto = strawberry_django.field(field_name="openTo")
    admission_fee: auto = strawberry_django.field(field_name="admissionFee")
    city: Optional["CityType"]
    category: Optional[LocationCategoryType]

    @strawberry.field
    def images(self, root) -> List[ImageLocationType]:
        return root.images.all()

    @strawberry.field
    def closed_days(self, root) -> List[WeekdayType]:
        return root.closedDays.all()


@strawberry_django.type(ImageHiking)
class ImageHikingType:
    id: auto
    created_at: auto

    @strawberry.field
    def image(self, root) -> ImageFieldType:
        return root.image

    @strawberry.field(name="imageMobile")
    def image_mobile(self, root) -> Optional[ImageFieldType]:
        return root.image_mobile


@strawberry_django.type(HikingLocation)
class HikingLocationType:
    order: auto
    location: "LocationType"


@strawberry_django.type(Hiking)
class HikingType:
    id: auto
    created_at: auto
    updated_at: auto
    name: auto
    name_en: str
    name_fr: str
    description: auto
    description_en: str
    description_fr: str
    city: Optional["CityType"]
    latitude: Optional[float]
    longitude: Optional[float]

    @strawberry.field
    def images(self, root) -> List[ImageHikingType]:
        return root.images.all()

    @strawberry.field
    def locations(self, root) -> List[HikingLocationType]:
        return root.hikinglocation_set.all().order_by("order")


@strawberry_django.type(EventCategory)
class EventCategoryType:
    id: auto
    name: auto
    name_en: str
    name_fr: str
    created_at: auto
    updated_at: auto


@strawberry_django.type(ImageEvent)
class ImageEventType:
    id: auto
    created_at: auto

    @strawberry.field
    def image(self, root) -> ImageFieldType:
        return root.image

    @strawberry.field(name="imageMobile")
    def image_mobile(self, root) -> Optional[ImageFieldType]:
        return root.image_mobile


@strawberry_django.type(Event)
class EventType:
    id: auto
    created_at: auto
    name: auto
    name_en: str
    name_fr: str
    start_date: auto = strawberry_django.field(field_name="startDate")
    end_date: auto = strawberry_django.field(field_name="endDate")
    time: auto
    price: auto
    link: auto
    short_link: auto
    short_id: auto
    boost: auto
    description: str
    description_en: str
    description_fr: str
    city: Optional["CityType"]
    category: Optional[EventCategoryType]
    location: Optional[LocationType]

    @strawberry.field
    def images(self, root) -> List[ImageEventType]:
        return root.images.all()


@strawberry_django.type(ImageAd)
class ImageAdType:
    id: auto
    created_at: auto

    @strawberry.field
    def image(self, root) -> ImageFieldType:
        return root.image

    @strawberry.field(name="imageMobile")
    def image_mobile(self, root) -> Optional[ImageFieldType]:
        return root.image_mobile


@strawberry_django.type(Country)
class CountryType:
    id: auto
    name: auto
    code2: auto
    code3: auto


@strawberry_django.type(Ad)
class AdType:
    id: auto
    created_at: auto
    updated_at: auto
    name: auto
    link: auto
    short_link: auto
    short_id: auto
    clicks: auto
    is_active: auto
    country: Optional[CountryType]
    city: Optional["CityType"]

    @strawberry.field(name="imageMobile")
    def image_mobile(self, root) -> Optional[ImageFieldType]:
        return root.image_mobile

    @strawberry.field(name="imageTablet")
    def image_tablet(self, root) -> Optional[ImageFieldType]:
        return root.image_tablet

    @strawberry.field
    def images(self, root) -> List[ImageAdType]:
        return root.images.all() if hasattr(root, "images") else []


@strawberry_django.type(Tip)
class TipType:
    id: auto
    created_at: auto
    updated_at: auto
    description: str
    description_en: str
    description_fr: str
    city: Optional["CityType"]


@strawberry_django.type(City)
class CityType:
    id: auto
    name: auto

    @strawberry.field
    def name_en(self, root) -> Optional[str]:
        translations = getattr(root, "translations", {})
        en_names = translations.get("en", [])
        return en_names[0] if en_names else root.name

    @strawberry.field
    def name_fr(self, root) -> Optional[str]:
        translations = getattr(root, "translations", {})
        fr_names = translations.get("fr", [])
        return fr_names[0] if fr_names else root.name

    @strawberry.field
    def name_ar(self, root) -> Optional[str]:
        translations = getattr(root, "translations", {})
        ar_names = translations.get("ar", [])
        return ar_names[0] if ar_names else root.name

    @strawberry.field
    def region(self, root) -> Optional[str]:
        return root.region.name if hasattr(root, "region") and root.region else None

    @strawberry.field
    def region_en(self, root) -> Optional[str]:
        if not hasattr(root, "region") or not root.region:
            return None
        translations = getattr(root.region, "translations", {})
        en_names = translations.get("en", [])
        return en_names[0] if en_names else root.region.name

    @strawberry.field
    def region_fr(self, root) -> Optional[str]:
        if not hasattr(root, "region") or not root.region:
            return None
        translations = getattr(root.region, "translations", {})
        fr_names = translations.get("fr", [])
        return fr_names[0] if fr_names else root.region.name

    @strawberry.field
    def region_ar(self, root) -> Optional[str]:
        if not hasattr(root, "region") or not root.region:
            return None
        translations = getattr(root.region, "translations", {})
        ar_names = translations.get("ar", [])
        return ar_names[0] if ar_names else root.region.name

    @strawberry.field
    def country(self, root) -> Optional[str]:
        return root.country.name if hasattr(root, "country") and root.country else None

    @strawberry.field
    def country_en(self, root) -> Optional[str]:
        if not hasattr(root, "country") or not root.country:
            return None
        translations = getattr(root.country, "translations", {})
        en_names = translations.get("en", [])
        return en_names[0] if en_names else root.country.name

    @strawberry.field
    def country_fr(self, root) -> Optional[str]:
        if not hasattr(root, "country") or not root.country:
            return None
        translations = getattr(root.country, "translations", {})
        fr_names = translations.get("fr", [])
        return fr_names[0] if fr_names else root.country.name

    @strawberry.field
    def country_ar(self, root) -> Optional[str]:
        if not hasattr(root, "country") or not root.country:
            return None
        translations = getattr(root.country, "translations", {})
        ar_names = translations.get("ar", [])
        return ar_names[0] if ar_names else root.country.name


@strawberry_django.type(PublicTransportType)
class PublicTransportTypeType:
    id: auto
    name: auto
    name_en: str
    name_fr: str


@strawberry_django.type(PublicTransportTime)
class PublicTransportTimeType:
    id: auto
    created_at: auto
    updated_at: auto
    time: auto


@strawberry_django.type(PublicTransport)
class PublicTransportNodeType:
    id: auto
    created_at: auto
    updated_at: auto
    city: Optional[CityType]
    bus_number: auto = strawberry_django.field(field_name="busNumber")

    @strawberry.field
    def public_transport_type(self, root) -> Optional[PublicTransportTypeType]:
        return root.publicTransportType

    @strawberry.field
    def from_region(self, root) -> Optional[str]:
        return root.fromRegion.name if root.fromRegion else None

    @strawberry.field
    def from_region_en(self, root) -> Optional[str]:
        if not root.fromRegion:
            return None
        translations = getattr(root.fromRegion, "translations", {})
        names = translations.get("en", [])
        return names[0] if names else root.fromRegion.name

    @strawberry.field
    def from_region_fr(self, root) -> Optional[str]:
        if not root.fromRegion:
            return None
        translations = getattr(root.fromRegion, "translations", {})
        names = translations.get("fr", [])
        return names[0] if names else root.fromRegion.name

    @strawberry.field
    def from_region_ar(self, root) -> Optional[str]:
        if not root.fromRegion:
            return None
        translations = getattr(root.fromRegion, "translations", {})
        names = translations.get("ar", [])
        return names[0] if names else root.fromRegion.name

    @strawberry.field
    def to_region(self, root) -> Optional[str]:
        return root.toRegion.name if root.toRegion else None

    @strawberry.field
    def to_region_en(self, root) -> Optional[str]:
        if not root.toRegion:
            return None
        translations = getattr(root.toRegion, "translations", {})
        names = translations.get("en", [])
        return names[0] if names else root.toRegion.name

    @strawberry.field
    def to_region_fr(self, root) -> Optional[str]:
        if not root.toRegion:
            return None
        translations = getattr(root.toRegion, "translations", {})
        names = translations.get("fr", [])
        return names[0] if names else root.toRegion.name

    @strawberry.field
    def to_region_ar(self, root) -> Optional[str]:
        if not root.toRegion:
            return None
        translations = getattr(root.toRegion, "translations", {})
        names = translations.get("ar", [])
        return names[0] if names else root.toRegion.name

    @strawberry.field
    def times(self, root) -> List[PublicTransportTimeType]:
        return root.publicTransportTimes.all()


# ═══════════════════════════════════════════════════════════════════════════════
# NOUVEAUX TYPES — Partners
# ═══════════════════════════════════════════════════════════════════════════════

@strawberry.type
class PartnerEventMediaType:
    id:         int
    file_url:   str
    media_type: str
    order:      int


@strawberry.type
class PartnerEventAccountType:
    id:               int
    title:            str
    description:      str
    start_date:       str
    end_date:         str
    link:             Optional[str]
    status:           str
    is_boosted:       bool
    is_published:     bool
    partner_name:     str
    days_until_start: int
    media:            List[PartnerEventMediaType]


@strawberry.type
class PartnerAdAccountType:
    id:           int
    title:        str
    image_url:    str
    redirect_url: str
    start_date:   str
    end_date:     str
    nb_days:      int
    status:       str
    partner_name: str


@strawberry.type
class PartnerAccountPublicType:
    id:           str
    company_name: str
    logo_url:     Optional[str]
    phone:        Optional[str]
    is_verified:  bool


# ── Helpers (synchrones — appelés dans sync_to_async) ─────────────────────────

def _serialize_partner_event(event: PartnerEvent) -> PartnerEventAccountType:
    media_list = [
        PartnerEventMediaType(
            id         = m.id,
            file_url   = m.file.url if m.file else '',
            media_type = m.media_type,
            order      = m.order,
        )
        for m in event.media.all()
    ]
    return PartnerEventAccountType(
        id               = event.id,
        title            = event.title,
        description      = event.description,
        start_date       = str(event.start_date),
        end_date         = str(event.end_date),
        link             = event.link,
        status           = event.status,
        is_boosted       = event.is_boosted,
        is_published     = event.is_published,
        partner_name     = event.partner.company_name,
        days_until_start = event.days_until_start,
        media            = media_list,
    )


def _serialize_partner_ad(ad: PartnerAd) -> PartnerAdAccountType:
    return PartnerAdAccountType(
        id           = ad.id,
        title        = ad.title,
        image_url    = ad.image.url if ad.image else '',
        redirect_url = ad.redirect_url,
        start_date   = str(ad.start_date),
        end_date     = str(ad.end_date),
        nb_days      = ad.nb_days,
        status       = ad.status,
        partner_name = ad.partner.company_name,
    )


def _serialize_partner_account(p: PartnerAccount) -> PartnerAccountPublicType:
    return PartnerAccountPublicType(
        id           = str(p.id),
        company_name = p.company_name,
        logo_url     = p.logo.url if p.logo else None,
        phone        = p.phone or None,
        is_verified  = p.is_verified,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# QUERY
# ═══════════════════════════════════════════════════════════════════════════════

@strawberry.type
class Query:

    # ── Queries existantes ────────────────────────────────────────────────────

    @strawberry.field
    def pages(self, is_active: Optional[bool] = None) -> List[PageType]:
        qs = Page.objects.all()
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        return qs

    @strawberry.field
    def page(self, slug: str) -> Optional[PageType]:
        return (
            Page.objects.filter(Q(slug_en=slug) | Q(slug_fr=slug))
            .filter(is_active=True)
            .first()
        )

    @strawberry.field
    def locations(
        self,
        city_id: Optional[int] = None,
        category_id: Optional[int] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = 0,
    ) -> List[LocationType]:
        qs = Location.objects.select_related("city", "country", "category").prefetch_related("images")
        if city_id is not None:
            qs = qs.filter(city_id=city_id)
        if category_id is not None:
            qs = qs.filter(category_id=category_id)
        if limit is not None:
            qs = qs[offset: offset + limit]
        return qs

    @strawberry.field
    def location(self, id: strawberry.ID) -> Optional[LocationType]:
        return Location.objects.prefetch_related("images").filter(pk=id).first()

    @strawberry.field
    def location_categories(self) -> List[LocationCategoryType]:
        return LocationCategory.objects.all()

    @strawberry.field
    def hikings(
        self,
        city_id: Optional[int] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = 0,
    ) -> List[HikingType]:
        qs = Hiking.objects.select_related("city").prefetch_related("images", "locations")
        if city_id is not None:
            qs = qs.filter(city_id=city_id)
        if limit is not None:
            qs = qs[offset: offset + limit]
        return qs

    @strawberry.field
    def hiking(self, id: strawberry.ID) -> Optional[HikingType]:
        return Hiking.objects.prefetch_related("images", "locations").filter(pk=id).first()

    @strawberry.field
    def events(
        self,
        city_id: Optional[int] = None,
        category_id: Optional[int] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = 0,
        boost: Optional[bool] = None,
    ) -> List[EventType]:
        qs = Event.objects.select_related("city", "category", "client", "location").prefetch_related("images")
        if city_id is not None:
            qs = qs.filter(city_id=city_id)
        if category_id is not None:
            qs = qs.filter(category_id=category_id)
        if boost is not None:
            qs = qs.filter(boost=boost)
        yesterday = timezone.now().date() - datetime.timedelta(days=1)
        qs = qs.filter(endDate__gte=yesterday)
        if limit is not None:
            qs = qs[offset: offset + limit]
        return qs

    @strawberry.field
    def event(self, id: strawberry.ID) -> Optional[EventType]:
        return Event.objects.prefetch_related("images", "location", "category").filter(pk=id).first()

    @strawberry.field
    def event_categories(self) -> List[EventCategoryType]:
        return EventCategory.objects.all()

    @strawberry.field
    def ads(
        self,
        city_id: Optional[int] = None,
        country_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = 0,
    ) -> List[AdType]:
        qs = Ad.objects.select_related("city", "country", "client")
        if city_id is not None:
            qs = qs.filter(city_id=city_id)
        if country_id is not None:
            qs = qs.filter(country_id=country_id)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        if limit is not None:
            qs = qs[offset: offset + limit]
        return qs

    @strawberry.field
    def ad(self, id: strawberry.ID) -> Optional[AdType]:
        return Ad.objects.filter(pk=id).first()

    @strawberry.field
    def tips(
        self,
        city_id: Optional[int] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = 0,
    ) -> List[TipType]:
        qs = Tip.objects.select_related("city")
        if city_id is not None:
            qs = qs.filter(city_id=city_id)
        if limit is not None:
            qs = qs[offset: offset + limit]
        return qs

    @strawberry.field
    def public_transports(
        self,
        city_id: Optional[int] = None,
        type_id: Optional[int] = None,
        from_region_id: Optional[int] = None,
        to_region_id: Optional[int] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = 0,
    ) -> List[PublicTransportNodeType]:
        qs = PublicTransport.objects.select_related(
            "city", "publicTransportType", "fromRegion", "toRegion"
        ).prefetch_related("publicTransportTimes")
        if city_id is not None:
            qs = qs.filter(city_id=city_id)
        if type_id is not None:
            qs = qs.filter(publicTransportType_id=type_id)
        if from_region_id is not None:
            qs = qs.filter(fromRegion_id=from_region_id)
        if to_region_id is not None:
            qs = qs.filter(toRegion_id=to_region_id)
        if limit is not None:
            qs = qs[offset: offset + limit]
        return qs

    @strawberry.field
    def public_transport(self, id: strawberry.ID) -> Optional[PublicTransportNodeType]:
        return (
            PublicTransport.objects.select_related(
                "city", "publicTransportType", "fromRegion", "toRegion"
            ).prefetch_related("publicTransportTimes").filter(pk=id).first()
        )

    @strawberry.field
    def public_transport_types(self) -> List[PublicTransportTypeType]:
        return PublicTransportType.objects.all()

    @strawberry.field
    def nearest_city(
        self, lat: float, lon: float, max_distance_km: Optional[float] = None
    ) -> Optional[CityType]:
        def haversine(lat1, lon1, lat2, lon2):
            R = 6371
            phi1 = math.radians(lat1)
            phi2 = math.radians(lat2)
            dphi = math.radians(lat2 - lat1)
            dlambda = math.radians(lon2 - lon1)
            a = (
                math.sin(dphi / 2) ** 2
                + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
            )
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            return R * c

        candidates = (
            City.objects.exclude(latitude__isnull=True)
            .exclude(longitude__isnull=True)
            .values("id", "name", "latitude", "longitude")
        )
        nearest = None
        nearest_distance = None
        for city in candidates:
            distance = haversine(lat, lon, float(city["latitude"]), float(city["longitude"]))
            if max_distance_km is not None and distance > max_distance_km:
                continue
            if nearest_distance is None or distance < nearest_distance:
                nearest_distance = distance
                nearest = city["id"]
        if nearest is None:
            return None
        return City.objects.filter(pk=nearest).first()

    @strawberry.field
    def partners(self) -> List[PartnerType]:
        return Partner.objects.all()

    @strawberry.field
    def sponsor(self, id: strawberry.ID) -> Optional[SponsorType]:
        return Sponsor.objects.filter(pk=id).first()

    @strawberry.field
    def sponsors(self) -> List[SponsorType]:
        return Sponsor.objects.all()

    # ── NOUVELLES Queries Partners — async avec sync_to_async ─────────────────

    @strawberry.field(description="Evenements partenaires publies")
    async def partner_events(
        self,
        boosted_only: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> List[PartnerEventAccountType]:
        def _get():
            qs = PartnerEvent.objects.filter(
                is_published=True,
                status__in=['approved', 'boosted']
            ).select_related('partner').prefetch_related('media').order_by('-is_boosted', 'start_date')
            if boosted_only:
                qs = qs.filter(is_boosted=True)
            return [_serialize_partner_event(e) for e in qs[offset:offset + limit]]
        return await sync_to_async(_get)()

    @strawberry.field(description="Un evenement partenaire par ID")
    async def partner_event(self, id: int) -> Optional[PartnerEventAccountType]:
        def _get():
            try:
                event = PartnerEvent.objects.select_related('partner').prefetch_related('media').get(
                    id=id, is_published=True
                )
                return _serialize_partner_event(event)
            except PartnerEvent.DoesNotExist:
                return None
        return await sync_to_async(_get)()

    @strawberry.field(description="Publicites partenaires actives")
    async def partner_ads(
        self,
        limit: int = 10,
        offset: int = 0,
    ) -> List[PartnerAdAccountType]:
        def _get():
            today = timezone.now().date()
            qs = PartnerAd.objects.filter(
                status='active',
                is_paid=True,
                start_date__lte=today,
                end_date__gte=today,
            ).select_related('partner').order_by('?')
            return [_serialize_partner_ad(a) for a in qs[offset:offset + limit]]
        return await sync_to_async(_get)()

    @strawberry.field(description="Partenaires verifies")
    async def partner_accounts(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> List[PartnerAccountPublicType]:
        def _get():
            qs = PartnerAccount.objects.filter(
                is_verified=True,
                is_active=True,
                account_frozen=False,
            ).order_by('company_name')
            return [_serialize_partner_account(p) for p in qs[offset:offset + limit]]
        return await sync_to_async(_get)()

    @strawberry.field(description="Un partenaire verifie par ID")
    async def partner_account(self, id: strawberry.ID) -> Optional[PartnerAccountPublicType]:
        def _get():
            try:
                p = PartnerAccount.objects.get(id=id, is_verified=True, is_active=True)
                return _serialize_partner_account(p)
            except PartnerAccount.DoesNotExist:
                return None
        return await sync_to_async(_get)()


# ═══════════════════════════════════════════════════════════════════════════════
# MUTATION (inchangee)
# ═══════════════════════════════════════════════════════════════════════════════

@strawberry.type
class SyncUserPreferencePayload:
    ok: bool


@strawberry.type
class RegisterDevicePayload:
    ok: bool
    message: Optional[str] = None


@strawberry.type
class Mutation:
    @strawberry.mutation
    def sync_user_preference(
        self,
        user_uid: uuid.UUID,
        first_visit: bool,
        traveling_with: str,
        interests: List[str],
        updated_at: datetime.datetime,
    ) -> SyncUserPreferencePayload:
        obj, created = UserPreference.objects.get_or_create(
            user_uid=user_uid,
            defaults={
                "first_visit": first_visit,
                "traveling_with": traveling_with,
                "interests": interests,
                "updated_at": updated_at,
            },
        )
        if not created and updated_at > obj.updated_at:
            obj.first_visit = first_visit
            obj.traveling_with = traveling_with
            obj.interests = interests
            obj.save()
        return SyncUserPreferencePayload(ok=True)

    @strawberry.mutation
    def forget_me(self, user_uid: uuid.UUID) -> SyncUserPreferencePayload:
        UserPreference.objects.filter(user_uid=user_uid).delete()
        return SyncUserPreferencePayload(ok=True)

    @strawberry.mutation
    def register_fcm_device(
        self,
        registration_id: str,
        type: str,
        name: Optional[str] = None,
        user_uid: Optional[uuid.UUID] = None,
    ) -> RegisterDevicePayload:
        try:
            from fcm_django.models import FCMDevice
            if type not in ["android", "ios", "web"]:
                return RegisterDevicePayload(
                    ok=False,
                    message=f"Invalid device type: {type}. Must be 'android', 'ios', or 'web'",
                )
            device, created = FCMDevice.objects.get_or_create(
                registration_id=registration_id,
                defaults={"type": type, "name": name or f"{type} device", "active": True},
            )
            if not created:
                device.type = type
                device.active = True
                if name:
                    device.name = name
                device.save()
            return RegisterDevicePayload(
                ok=True,
                message="Device registered successfully" if created else "Device updated successfully",
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error registering FCM device: {e}", exc_info=True)
            return RegisterDevicePayload(ok=False, message=f"Error registering device: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# SUBSCRIPTION — temps reel Partners
# ═══════════════════════════════════════════════════════════════════════════════

@strawberry.type
class Subscription:

    @strawberry.subscription(description="Nouvel evenement partenaire publie")
    async def new_partner_event(self) -> PartnerEventAccountType:
        seen_ids = set(
            await sync_to_async(list)(
                PartnerEvent.objects.filter(is_published=True).values_list('id', flat=True)
            )
        )
        while True:
            await asyncio.sleep(5)
            current_ids = set(
                await sync_to_async(list)(
                    PartnerEvent.objects.filter(is_published=True).values_list('id', flat=True)
                )
            )
            for event_id in current_ids - seen_ids:
                event = await sync_to_async(
                    PartnerEvent.objects.select_related('partner').prefetch_related('media').get
                )(id=event_id)
                yield _serialize_partner_event(event)
            seen_ids = current_ids

    @strawberry.subscription(description="Nouvelle publicite partenaire active")
    async def new_partner_ad(self) -> PartnerAdAccountType:
        seen_ids = set(
            await sync_to_async(list)(
                PartnerAd.objects.filter(status='active', is_paid=True).values_list('id', flat=True)
            )
        )
        while True:
            await asyncio.sleep(10)
            current_ids = set(
                await sync_to_async(list)(
                    PartnerAd.objects.filter(status='active', is_paid=True).values_list('id', flat=True)
                )
            )
            for ad_id in current_ids - seen_ids:
                ad = await sync_to_async(
                    PartnerAd.objects.select_related('partner').get
                )(id=ad_id)
                yield _serialize_partner_ad(ad)
            seen_ids = current_ids


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA FINAL
# ═══════════════════════════════════════════════════════════════════════════════

extensions = []
if not settings.DEBUG:
    extensions.append(AddValidationRules([NoSchemaIntrospectionCustomRule]))

schema = strawberry.Schema(
    query        = Query,
    mutation     = Mutation,
    subscription = Subscription,
    extensions   = extensions,
)
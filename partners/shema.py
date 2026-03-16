# partners/schema.py
import strawberry
import strawberry_django
from strawberry import auto
from strawberry.types import Info
from typing import List, Optional
import asyncio
from asgiref.sync import sync_to_async

from partners.models import Partner, PartnerEvent, PartnerEventMedia, PartnerAd


# ── Types ─────────────────────────────────────────────────────────────────────

@strawberry.type
class PartnerEventMediaType:
    id:         int
    file:       str
    media_type: str
    order:      int

    @strawberry.field
    def file_url(self) -> str:
        return self.file


@strawberry.type
class PartnerEventType:
    id:          int
    title:       str
    description: str
    start_date:  str
    end_date:    str
    link:        Optional[str]
    status:      str
    is_boosted:  bool
    is_published: bool
    partner_name: str
    days_until_start: int
    media:       List[PartnerEventMediaType]


@strawberry.type
class PartnerAdType:
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
class PartnerPublicType:
    id:           str
    company_name: str
    logo_url:     Optional[str]
    phone:        Optional[str]
    is_verified:  bool


@strawberry.type
class PartnerContractType:
    id:            int
    period:        str
    payment_type:  str
    start_date:    str
    end_date:      str
    total_amount:  float
    monthly_amount: float
    is_paid:       bool


# ── Helpers ───────────────────────────────────────────────────────────────────

def serialize_event(event: PartnerEvent) -> PartnerEventType:
    media_list = [
        PartnerEventMediaType(
            id         = m.id,
            file       = m.file.url if m.file else '',
            media_type = m.media_type,
            order      = m.order,
        )
        for m in event.media.all()
    ]
    return PartnerEventType(
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


def serialize_ad(ad: PartnerAd) -> PartnerAdType:
    return PartnerAdType(
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


def serialize_partner(partner: Partner) -> PartnerPublicType:
    return PartnerPublicType(
        id           = str(partner.id),
        company_name = partner.company_name,
        logo_url     = partner.logo.url if partner.logo else None,
        phone        = partner.phone or None,
        is_verified  = partner.is_verified,
    )


# ── Queries ───────────────────────────────────────────────────────────────────

@strawberry.type
class PartnerQuery:

    @strawberry.field(description="Tous les événements publiés")
    def partner_events(
        self,
        boosted_only: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> List[PartnerEventType]:
        qs = PartnerEvent.objects.filter(
            is_published=True,
            status__in=['approved', 'boosted']
        ).select_related('partner').prefetch_related('media').order_by('-is_boosted', 'start_date')

        if boosted_only:
            qs = qs.filter(is_boosted=True)

        return [serialize_event(e) for e in qs[offset:offset + limit]]

    @strawberry.field(description="Un événement par ID")
    def partner_event(self, id: int) -> Optional[PartnerEventType]:
        try:
            event = PartnerEvent.objects.select_related('partner').prefetch_related('media').get(
                id=id, is_published=True
            )
            return serialize_event(event)
        except PartnerEvent.DoesNotExist:
            return None

    @strawberry.field(description="Toutes les publicités actives")
    def partner_ads(
        self,
        limit: int = 10,
        offset: int = 0,
    ) -> List[PartnerAdType]:
        from django.utils import timezone
        today = timezone.now().date()
        qs = PartnerAd.objects.filter(
            status='active',
            is_paid=True,
            start_date__lte=today,
            end_date__gte=today,
        ).select_related('partner').order_by('?')  # ordre aléatoire
        return [serialize_ad(a) for a in qs[offset:offset + limit]]

    @strawberry.field(description="Liste des partenaires vérifiés")
    def partners(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> List[PartnerPublicType]:
        qs = Partner.objects.filter(
            is_verified=True,
            is_active=True,
            account_frozen=False,
        ).order_by('company_name')
        return [serialize_partner(p) for p in qs[offset:offset + limit]]

    @strawberry.field(description="Un partenaire par ID")
    def partner(self, id: strawberry.ID) -> Optional[PartnerPublicType]:
        try:
            p = Partner.objects.get(id=id, is_verified=True, is_active=True)
            return serialize_partner(p)
        except Partner.DoesNotExist:
            return None


# ── Subscriptions ─────────────────────────────────────────────────────────────

@strawberry.type
class PartnerSubscription:

    @strawberry.subscription(description="Nouvel événement publié en temps réel")
    async def new_partner_event(self) -> PartnerEventType:
        """
        Émet un événement chaque fois qu'un nouveau PartnerEvent
        est approuvé/publié. Polling toutes les 5 secondes.
        """
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
            new_ids = current_ids - seen_ids
            for event_id in new_ids:
                event = await sync_to_async(
                    PartnerEvent.objects.select_related('partner').prefetch_related('media').get
                )(id=event_id)
                yield serialize_event(event)
            seen_ids = current_ids

    @strawberry.subscription(description="Nouvelle publicité active en temps réel")
    async def new_partner_ad(self) -> PartnerAdType:
        """
        Émet une publicité chaque fois qu'une nouvelle PartnerAd
        devient active. Polling toutes les 10 secondes.
        """
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
            new_ids = current_ids - seen_ids
            for ad_id in new_ids:
                ad = await sync_to_async(
                    PartnerAd.objects.select_related('partner').get
                )(id=ad_id)
                yield serialize_ad(ad)
            seen_ids = current_ids
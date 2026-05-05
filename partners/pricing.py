# partners/pricing.py

# ── Abonnements ───────────────────────────────────────────────────────────────
# 3 catégories de packages :
# CAT 1 : Abonnement durée (3 mois / 6 mois / 1 an / 10 mois)
# CAT 2 : Prix boost événement par jour (2 TND/jour)
# CAT 3 : Publicités (2 TND/jour)

SUBSCRIPTION_PRICES = {
    '1_month':   {'total': 10.000,  'monthly': 10.000},   # 1 mois
    '3_months':  {'total': 25.000,  'monthly': 8.333},    # 3 mois
    '6_months':  {'total': 50.000,  'monthly': 8.333},    # 6 mois
    '10_months': {'total': 80.000,  'monthly': 8.000},    # 10 mois
    '12_months': {'total': 100.000, 'monthly': 8.333},    # 1 an
}

PERIOD_MONTHS = {
    '1_month':   1,
    '3_months':  3,
    '6_months':  6,
    '10_months': 10,
    '12_months': 12,
}

from django.utils.translation import gettext_lazy as _

PERIOD_LABELS = {
    '1_month':   _('1 month'),
    '3_months':  _('3 months'),
    '6_months':  _('6 months'),
    '10_months': _('10 months'),
    '12_months': _('1 year'),
}

# ── CAT 2 : Prix boost événement ──────────────────────────────────────────────
BOOST_PRICE_PER_DAY = 2.000   # 2 TND par jour
BOOST_FIXED_PRICE   = 20.000  # OU prix fixe si tu préfères

# ── CAT 3 : Prix publicité ────────────────────────────────────────────────────
AD_PRICE_PER_DAY = 2.000      # 2 TND par jour (changé de 5 → 2)


def calculate_subscription_price(period: str, payment_type: str, coupon_discount: float = 0) -> dict:
    """
    Calcule le prix d'un abonnement.
    coupon_discount : pourcentage de réduction (ex: 20 = 20%)
    """
    prices  = SUBSCRIPTION_PRICES.get(period, {})
    months  = PERIOD_MONTHS.get(period, 1)
    total   = prices.get('total', 0)
    monthly = prices.get('monthly', 0)

    # Applique la réduction coupon
    if coupon_discount > 0:
        reduction = total * (coupon_discount / 100)
        total     = round(total - reduction, 3)
        monthly   = round(total / months, 3)

    first_payment = total if payment_type == 'total' else monthly

    return {
        'total':          total,
        'monthly':        monthly,
        'months':         months,
        'first_payment':  first_payment,
        'payment_type':   payment_type,
        'period':         period,
        'period_label':   PERIOD_LABELS.get(period, ''),
        'discount':       coupon_discount,
    }


def calculate_ad_price(nb_days: int, coupon_discount: float = 0) -> float:
    """Calcule le prix d'une publicité avec réduction optionnelle."""
    total = AD_PRICE_PER_DAY * nb_days
    if coupon_discount > 0:
        total = total * (1 - coupon_discount / 100)
    return round(total, 3)
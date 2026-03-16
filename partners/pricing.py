# partners/pricing.py
# Prix abonnements en TND

SUBSCRIPTION_PRICES = {
    '1_month':   {'total': 50.000,  'monthly': 50.000},
    '3_months':  {'total': 130.000, 'monthly': 43.333},
    '6_months':  {'total': 240.000, 'monthly': 40.000},
    '9_months':  {'total': 330.000, 'monthly': 36.667},
    '12_months': {'total': 400.000, 'monthly': 33.333},
}

PERIOD_MONTHS = {
    '1_month':   1,
    '3_months':  3,
    '6_months':  6,
    '9_months':  9,
    '12_months': 12,
}

PERIOD_LABELS = {
    '1_month':   '1 Mois',
    '3_months':  '3 Mois',
    '6_months':  '6 Mois',
    '9_months':  '9 Mois',
    '12_months': '12 Mois (1 An)',
}

AD_PRICE_PER_DAY = 5.000
BOOST_PRICE      = 20.000


def calculate_subscription_price(period: str, payment_type: str) -> dict:
    """
    Retourne les détails de prix pour un abonnement.
    payment_type: 'total' ou 'monthly'
    """
    prices  = SUBSCRIPTION_PRICES.get(period, {})
    months  = PERIOD_MONTHS.get(period, 1)
    total   = prices.get('total', 0)
    monthly = prices.get('monthly', 0)

    if payment_type == 'total':
        first_payment = total
    else:
        first_payment = monthly

    return {
        'total':         total,
        'monthly':       monthly,
        'months':        months,
        'first_payment': first_payment,
        'payment_type':  payment_type,
        'period':        period,
        'period_label':  PERIOD_LABELS.get(period, ''),
    }
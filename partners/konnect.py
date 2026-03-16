import requests
from django.conf import settings


KONNECT_BASE_URL  = getattr(settings, 'KONNECT_BASE_URL', 'https://api.sandbox.konnect.network/api/v2')
KONNECT_API_KEY   = getattr(settings, 'KONNECT_API_KEY', '')
KONNECT_WALLET_ID = getattr(settings, 'KONNECT_RECEIVER_WALLET_ID', '')


def init_payment(amount_millimes: int, order_id: str, description: str, webhook_url: str, success_url: str, fail_url: str) -> dict:
    """
    Initialise un paiement Konnect.
    amount_millimes : montant en millimes (ex: 20000 = 20.000 TND)
    Retourne : { 'payUrl': '...', 'paymentRef': '...' } ou { 'error': '...' }
    """
    headers = {
        'x-api-key': KONNECT_API_KEY,
        'Content-Type': 'application/json',
    }

    payload = {
        "receiverWalletId": KONNECT_WALLET_ID,
        "token":            "TND",
        "amount":           amount_millimes,
        "type":             "immediate",
        "description":      description,
        "acceptedPaymentMethods": ["wallet", "bank_card", "e-DINAR"],
        "lifespan":         10,
        "checkoutForm":     True,
        "addPaymentFeesToAmount": False,
        "firstName":        "",
        "lastName":         "",
        "orderId":          order_id,
        "webhook":          webhook_url,
        "successUrl":       success_url,
        "failUrl":          fail_url,
        "theme":            "light",
    }

    try:
        resp = requests.post(
            f"{KONNECT_BASE_URL}/payments/init-payment",
            json=payload,
            headers=headers,
            timeout=10,
        )
        data = resp.json()
        if resp.status_code == 200 and data.get('payUrl'):
            return {
                'payUrl':     data['payUrl'],
                'paymentRef': data.get('paymentRef', ''),
            }
        return {'error': data.get('message', 'Erreur Konnect')}
    except Exception as e:
        return {'error': str(e)}


def verify_payment(payment_ref: str) -> dict:
    """
    Vérifie le statut d'un paiement Konnect.
    Retourne : { 'paid': True/False, 'status': '...' }
    """
    headers = {'x-api-key': KONNECT_API_KEY}
    try:
        resp = requests.get(
            f"{KONNECT_BASE_URL}/payments/{payment_ref}",
            headers=headers,
            timeout=10,
        )
        data = resp.json()
        payment = data.get('payment', {})
        status  = payment.get('status', '')
        return {
            'paid':   status == 'completed',
            'status': status,
        }
    except Exception as e:
        return {'paid': False, 'status': 'error', 'error': str(e)}
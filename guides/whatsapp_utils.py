import logging
import re
from django.conf import settings

logger = logging.getLogger(__name__)


def _normalize_phone(phone: str) -> str | None:
    """
    Normalise un numéro tunisien vers le format E.164 (+216XXXXXXXX).
    Retourne None si le numéro est vide ou invalide.
    """
    if not phone:
        return None

    # Supprime tout ce qui n'est pas chiffre ou +
    cleaned = re.sub(r"[^\d+]", "", phone.strip())

    # Déjà en format international
    if cleaned.startswith("+"):
        return cleaned if len(cleaned) >= 8 else None

    # Préfixe tunisien par défaut si 8 chiffres
    if re.match(r"^\d{8}$", cleaned):
        return f"+216{cleaned}"

    # Commence par 216 sans le +
    if cleaned.startswith("216") and len(cleaned) == 11:
        return f"+{cleaned}"

    return cleaned if cleaned else None


def send_whatsapp_message(to_phone: str, message: str) -> bool:
    """
    Envoie un message WhatsApp via Twilio.

    Prérequis dans settings.py :
        TWILIO_ACCOUNT_SID  = "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        TWILIO_AUTH_TOKEN   = "your_auth_token"
        TWILIO_WHATSAPP_FROM = "whatsapp:+14155238886"   # sandbox Twilio
        WHATSAPP_ENABLED    = True   # mettre False pour désactiver sans toucher le code

    Retourne True si l'envoi a réussi, False sinon.
    """
    if not getattr(settings, "WHATSAPP_ENABLED", False):
        logger.info("[WhatsApp] Désactivé (WHATSAPP_ENABLED=False). Message non envoyé.")
        return False

    account_sid  = getattr(settings, "TWILIO_ACCOUNT_SID",   None)
    auth_token   = getattr(settings, "TWILIO_AUTH_TOKEN",    None)
    from_number  = getattr(settings, "TWILIO_WHATSAPP_FROM", None)

    if not all([account_sid, auth_token, from_number]):
        logger.warning("[WhatsApp] Configuration Twilio incomplète. Vérifiez TWILIO_* dans settings.py.")
        return False

    normalized = _normalize_phone(to_phone)
    if not normalized:
        logger.warning("[WhatsApp] Numéro invalide ou vide : %s", to_phone)
        return False

    to_whatsapp = f"whatsapp:{normalized}"

    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        msg = client.messages.create(
            body=message,
            from_=from_number,
            to=to_whatsapp,
        )
        logger.info("[WhatsApp] Message envoyé à %s — SID : %s", to_whatsapp, msg.sid)
        return True

    except ImportError:
        logger.error("[WhatsApp] twilio n'est pas installé. Lancez : pip install twilio")
        return False

    except Exception as exc:  # noqa: BLE001
        logger.error("[WhatsApp] Échec de l'envoi à %s : %s", to_whatsapp, exc)
        return False


def send_new_suggestion_whatsapp(guide, suggestion) -> bool:
    """
    Notifie le guide par WhatsApp d'une nouvelle demande de réservation.
    La langue du message suit guide.preferred_language ('fr' ou 'en').
    """
    guide_name = guide.user.get_full_name() or guide.user.username
    lang = getattr(guide, 'preferred_language', 'fr')

    # Calcul du montant (total_price = 0 à la création, avant approve())
    adults_subtotal   = round(suggestion.nb_adults * float(guide.price_adult), 3)
    children_subtotal = round(suggestion.nb_children_over_6 * float(guide.price_child), 3)
    total_price       = round(adults_subtotal + children_subtotal, 3)
    commission        = float(suggestion.commission_rate)
    net_amount        = round(total_price * (1 - commission / 100), 3)

    site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')

    if lang == 'en':
        # ── English message ───────────────────────────────────────────────
        group_line = f"{suggestion.nb_adults} adult(s)"
        if suggestion.nb_children_over_6:
            group_line += f", {suggestion.nb_children_over_6} child(ren) >6 yrs"
        if suggestion.nb_children_under_6:
            group_line += f", {suggestion.nb_children_under_6} child(ren) <6 yrs"

        message = (
            f"🔔 *New Booking Request — FielMedina*\n\n"
            f"Hello *{guide_name}*,\n\n"
            f"You have received a new guided tour request:\n\n"
            f"👤 *Client:* {suggestion.client_name}\n"
            f"📅 *Requested date:* {suggestion.date.strftime('%d/%m/%Y')}\n"
            f"👥 *Group:* {group_line}\n"
            f"💰 *Estimated amount:* {total_price:.3f} TND\n"
            f"💵 *Net after commission ({commission:.0f}%):* {net_amount:.3f} TND\n\n"
            f"Log in to your dashboard to accept or decline this request.\n"
            f"{site_url}/guides/suggestions/"
        )
    else:
        # ── French message (default) ──────────────────────────────────────
        group_line = f"{suggestion.nb_adults} adulte(s)"
        if suggestion.nb_children_over_6:
            group_line += f", {suggestion.nb_children_over_6} enfant(s) >6 ans"
        if suggestion.nb_children_under_6:
            group_line += f", {suggestion.nb_children_under_6} enfant(s) <6 ans"

        message = (
            f"🔔 *Nouvelle demande de réservation — FielMedina*\n\n"
            f"Bonjour *{guide_name}*,\n\n"
            f"Vous avez reçu une nouvelle demande de visite guidée :\n\n"
            f"👤 *Client :* {suggestion.client_name}\n"
            f"📅 *Date souhaitée :* {suggestion.date.strftime('%d/%m/%Y')}\n"
            f"👥 *Groupe :* {group_line}\n"
            f"💰 *Montant estimé :* {total_price:.3f} TND\n"
            f"💵 *Net après commission ({commission:.0f}%) :* {net_amount:.3f} TND\n\n"
            f"Connectez-vous à votre tableau de bord pour accepter ou refuser cette demande.\n"
            f"{site_url}/guides/suggestions/"
        )

    return send_whatsapp_message(guide.phone, message)
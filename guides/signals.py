import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _notify_guide_new_suggestion(guide, suggestion):
    """
    Déclenche les notifications email et WhatsApp pour une nouvelle suggestion.
    Chaque canal est isolé dans son propre try/except pour qu'une erreur d'un
    canal ne bloque pas l'autre.
    """
    # ── Email ──────────────────────────────────────────────────────────────
    try:
        from .email_utils import send_new_suggestion_email
        send_new_suggestion_email(guide, suggestion)
        logger.info(
            "[Notification] Email envoyé au guide %s pour la suggestion #%s",
            guide.email, suggestion.pk
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "[Notification] Échec email pour le guide %s (suggestion #%s) : %s",
            guide.email, suggestion.pk, exc
        )

    # ── WhatsApp ───────────────────────────────────────────────────────────
    try:
        from .whatsapp_utils import send_new_suggestion_whatsapp
        sent = send_new_suggestion_whatsapp(guide, suggestion)
        if sent:
            logger.info(
                "[Notification] WhatsApp envoyé au guide %s pour la suggestion #%s",
                guide.phone, suggestion.pk
            )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "[Notification] Échec WhatsApp pour le guide %s (suggestion #%s) : %s",
            guide.phone, suggestion.pk, exc
        )


@receiver(post_save, sender='guides.GuideSuggestion')
def on_new_suggestion(sender, instance, created, **kwargs):
    """
    Se déclenche après chaque sauvegarde d'un GuideSuggestion.
    N'envoie la notification QUE lors de la création (created=True).
    """
    if not created:
        return

    guide = instance.guide
    _notify_guide_new_suggestion(guide, instance)
"""
Commande Django pour vérifier les abonnements expirés et envoyer des alertes.
À exécuter quotidiennement via cron ou Celery.

Usage:
    python manage.py check_subscriptions
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from partners.models import Partner


class Command(BaseCommand):
    help = 'Vérifie les abonnements et gère les alertes + suspensions'

    def handle(self, *args, **kwargs):
        today    = timezone.now().date()
        partners = Partner.objects.filter(is_active=True, contract_end__isnull=False)

        frozen_count  = 0
        alerted_count = 0

        for partner in partners:
            days = (partner.contract_end - today).days

            # ── Suspension après 7 jours d'expiration ──────────────────
            if days <= -7 and not partner.account_frozen:
                partner.account_frozen = True
                partner.save(update_fields=['account_frozen'])
                frozen_count += 1
                self.stdout.write(
                    self.style.WARNING(f"[FROZEN] {partner.company_name} ({partner.email})")
                )
                self._send_email(
                    partner.email,
                    "Votre compte FielMedina a été suspendu",
                    f"""Bonjour {partner.company_name},

Votre abonnement FielMedina a expiré depuis plus de 7 jours.
Votre compte a été suspendu.

Renouvelez votre abonnement sur : http://127.0.0.1:8000/partners/subscription/

Cordialement,
L'équipe FielMedina"""
                )

            # ── Alertes expiration prochaine ────────────────────────────
            elif days in [7, 3, 1] and not partner.account_frozen:
                alerted_count += 1
                self.stdout.write(
                    self.style.NOTICE(f"[ALERT {days}j] {partner.company_name} ({partner.email})")
                )
                self._send_email(
                    partner.email,
                    f"Votre abonnement FielMedina expire dans {days} jour(s)",
                    f"""Bonjour {partner.company_name},

Votre abonnement FielMedina expire dans {days} jour(s) (le {partner.contract_end}).

Renouvelez maintenant pour continuer à profiter de nos services :
http://127.0.0.1:8000/partners/subscription/

Cordialement,
L'équipe FielMedina"""
                )

            # ── Réactivation si abonnement renouvelé ───────────────────
            elif days > 0 and partner.account_frozen:
                partner.account_frozen = False
                partner.save(update_fields=['account_frozen'])
                self.stdout.write(
                    self.style.SUCCESS(f"[REACTIVATED] {partner.company_name}")
                )

        self.stdout.write(self.style.SUCCESS(
            f"Done — {frozen_count} compte(s) suspendu(s), {alerted_count} alerte(s) envoyée(s)"
        ))

    def _send_email(self, to_email: str, subject: str, body: str):
        """Envoie un email — nécessite EMAIL_* dans settings.py"""
        try:
            send_mail(
                subject      = subject,
                message      = body,
                from_email   = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@fielmedina.com'),
                recipient_list = [to_email],
                fail_silently  = True,
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Email error: {e}"))
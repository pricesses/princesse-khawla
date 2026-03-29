"""
python manage.py check_subscriptions
Lance quotidiennement pour gérer alertes + suspensions + notifications admin impayé 10j
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from partners.models import Partner, AdminNotification


class Command(BaseCommand):
    help = 'Vérifie les abonnements — alertes, suspensions, notifications admin'

    def handle(self, *args, **kwargs):
        today    = timezone.now().date()
        partners = Partner.objects.filter(is_active=True, contract_end__isnull=False)

        frozen_count  = 0
        alerted_count = 0
        notif_count   = 0

        for partner in partners:
            days = (partner.contract_end - today).days

            # ── Notification admin si impayé depuis > 10 jours ────────────────
            if days <= -10 and not partner.account_frozen:
                # Vérifie qu'une notification n'existe pas déjà ce jour
                already_notified = AdminNotification.objects.filter(
                    partner    = partner,
                    type       = 'unpaid_subscription',
                    created_at__date = today,
                ).exists()

                if not already_notified:
                    AdminNotification.objects.create(
                        partner = partner,
                        type    = 'unpaid_subscription',
                        message = (
                            f"⚠️ {partner.company_name} n'a pas renouvelé son abonnement "
                            f"depuis {abs(days)} jours (expiré le {partner.contract_end}). "
                            f"Action requise : suspendre ou contacter le partenaire."
                        ),
                    )
                    notif_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"[NOTIF ADMIN] {partner.company_name} — impayé {abs(days)}j"
                        )
                    )

            # ── Suspension après 10 jours d'expiration ────────────────────────
            if days <= -10 and not partner.account_frozen:
                partner.account_frozen = True
                partner.save(update_fields=['account_frozen'])
                frozen_count += 1
                self.stdout.write(
                    self.style.WARNING(f"[FROZEN] {partner.company_name}")
                )

            # ── Alertes expiration prochaine (7j, 3j, 1j) ────────────────────
            elif days in [7, 3, 1] and not partner.account_frozen:
                alerted_count += 1
                self.stdout.write(
                    self.style.NOTICE(
                        f"[ALERT {days}j] {partner.company_name} ({partner.email})"
                    )
                )
                # Crée une notification admin aussi
                AdminNotification.objects.get_or_create(
                    partner = partner,
                    type    = 'unpaid_subscription',
                    defaults={
                        'message': (
                            f"⏰ Abonnement de {partner.company_name} expire dans "
                            f"{days} jour(s) (le {partner.contract_end})."
                        )
                    }
                )

            # ── Réactivation si contrat renouvelé ─────────────────────────────
            elif days > 0 and partner.account_frozen:
                partner.account_frozen = False
                partner.save(update_fields=['account_frozen'])
                self.stdout.write(
                    self.style.SUCCESS(f"[REACTIVATED] {partner.company_name}")
                )

        self.stdout.write(self.style.SUCCESS(
            f"\nDone — {frozen_count} suspendu(s), "
            f"{alerted_count} alerte(s), "
            f"{notif_count} notification(s) admin créée(s)"
        ))
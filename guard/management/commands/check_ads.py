from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from guard.models import Ad


class Command(BaseCommand):
    help = "Desactive les Ads non cliquees depuis 10 minutes"

    def handle(self, *args, **kwargs):
        ads = Ad.objects.all()
        if not ads.exists():
            self.stdout.write("Aucune Ad trouvee.")
            return

        limit = timezone.now() - timedelta(minutes=10)

        for ad in ads:
            if not ad.last_clicked_at or ad.last_clicked_at < limit:
                is_active = False
            else:
                is_active = True

            if ad.is_active != is_active:
                ad.is_active = is_active
                ad.save(update_fields=['is_active'])

            status = "Active" if is_active else "Inactive"
            self.stdout.write(f"{ad.name} ({ad.link}) -> {status}")

        self.stdout.write(self.style.SUCCESS("Verification terminee"))

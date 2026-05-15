from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
import secrets

class Guide(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='guide_profile')
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to='guides/photos/', null=True, blank=True)
    description = models.TextField(blank=True)
    languages = models.CharField(max_length=255, blank=True)
    accepts_children = models.BooleanField(default=True)

    price_adult = models.DecimalField(max_digits=10, decimal_places=3, default=0.000)
    price_child = models.DecimalField(max_digits=10, decimal_places=3, default=0.000)

    wallet_balance = models.DecimalField(max_digits=10, decimal_places=3, default=0.000)

    # --- Deux notes séparées ---
    # Note clients : moyenne automatique calculée depuis GuideReview
    client_stars = models.FloatField(default=0.0)
    # Note administrateur : saisie manuellement par l'admin (0-5, pas de 0.5)
    admin_stars = models.FloatField(default=0.0)

    # Champ legacy conservé pour compatibilité ascendante
    # (affiche la moyenne pondérée des deux notes)
    stars = models.FloatField(default=0.0)

    # Langue préférée pour les notifications (email + WhatsApp)
    LANGUAGE_CHOICES = [('fr', 'Français'), ('en', 'English')]
    preferred_language = models.CharField(
        max_length=5,
        choices=LANGUAGE_CHOICES,
        default='fr',
        help_text="Langue des notifications envoyées au guide"
    )

    # Email change fields
    pending_email = models.EmailField(blank=True, null=True)
    email_change_token = models.CharField(max_length=64, blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Guide: {self.user.get_full_name() or self.user.username} ({self.email})"

    def update_client_stars(self):
        """Recalcule la note clients depuis les GuideReview et met à jour stars (moyenne globale)."""
        reviews = self.reviews.all()
        if reviews.exists():
            avg = reviews.aggregate(models.Avg('rating'))['rating__avg']
            self.client_stars = round(avg, 1)
        else:
            self.client_stars = 0.0
        self._update_global_stars()
        self.save(update_fields=['client_stars', 'stars'])

    def update_admin_stars(self, value: float):
        """Met à jour la note administrateur et recalcule la moyenne globale."""
        self.admin_stars = round(max(0.0, min(5.0, value)), 1)
        self._update_global_stars()
        self.save(update_fields=['admin_stars', 'stars'])

    def _update_global_stars(self):
        """
        Calcule la note globale (stars) comme moyenne pondérée :
        - 60 % note clients
        - 40 % note admin
        Si l'une des deux est à 0, on utilise l'autre seule.
        """
        c = self.client_stars
        a = self.admin_stars
        if c > 0 and a > 0:
            self.stars = round(c * 0.6 + a * 0.4, 1)
        elif c > 0:
            self.stars = c
        elif a > 0:
            self.stars = a
        else:
            self.stars = 0.0

    # ── Rétro-compatibilité ──────────────────────────────────────────────────
    def update_stars(self):
        """Alias conservé pour ne pas casser l'ancien code."""
        self.update_client_stars()

    @property
    def total_brut(self):
        from decimal import Decimal
        result = self.suggestions.filter(status='approved').aggregate(
            s=models.Sum('total_price')
        )['s']
        return result or Decimal('0')

    @property
    def total_commission(self):
        approved = self.suggestions.filter(status='approved')
        return sum(s.commission_amount for s in approved)


class GuideReview(models.Model):
    guide = models.ForeignKey(Guide, on_delete=models.CASCADE, related_name='reviews')
    client_name = models.CharField(max_length=255)
    rating = models.PositiveIntegerField(default=5)  # 1-5
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.guide.update_client_stars()

    def delete(self, *args, **kwargs):
        guide = self.guide
        super().delete(*args, **kwargs)
        guide.update_client_stars()

    def __str__(self):
        return f"Review for {self.guide} by {self.client_name}"


class GuideAdminRating(models.Model):
    """
    Évaluation de l'administrateur pour un guide.
    Un seul enregistrement par guide (OneToOne).
    L'admin peut mettre à jour la note et laisser un commentaire interne.
    """
    guide = models.OneToOneField(Guide, on_delete=models.CASCADE, related_name='admin_rating')
    rating = models.FloatField(
        default=0.0,
        help_text="Note de 0 à 5 (pas de 0.5)"
    )
    comment = models.TextField(
        blank=True,
        help_text="Commentaire interne de l'administrateur (non visible par le guide)"
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        'auth.User',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='admin_ratings_given'
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Propage la note vers le guide
        self.guide.update_admin_stars(self.rating)

    def __str__(self):
        return f"Admin rating for {self.guide} : {self.rating}/5"


class GuideSuggestion(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
    ]
    guide = models.ForeignKey(Guide, on_delete=models.CASCADE, related_name='suggestions')
    client_name = models.CharField(max_length=255)
    client_email = models.EmailField()
    date = models.DateField()
    message = models.TextField(blank=True)
    nb_adults = models.PositiveIntegerField(default=1)
    nb_children_under_6 = models.PositiveIntegerField(default=0)
    nb_children_over_6 = models.PositiveIntegerField(default=0)

    total_price = models.DecimalField(max_digits=10, decimal_places=3, default=0.000)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def commission_amount(self):
        from decimal import Decimal
        return round(self.total_price * self.commission_rate / Decimal('100'), 3)

    @property
    def net_guide_amount(self):
        return round(self.total_price - self.commission_amount, 3)

    def calculate_total(self):
        price = (self.nb_adults * self.guide.price_adult) + (self.nb_children_over_6 * self.guide.price_child)
        self.total_price = price
        return price

    def save(self, *args, **kwargs):
        if self.total_price == 0 and self.guide_id:
            self.calculate_total()
        super().save(*args, **kwargs)

    def approve(self):
        if self.status != 'approved':
            self.status = 'approved'
            self.calculate_total()
            self.save()

            self.guide.wallet_balance += self.net_guide_amount
            self.guide.save(update_fields=['wallet_balance'])

            GuideAvailability.objects.get_or_create(guide=self.guide, date=self.date, is_available=False)

            GuideWalletTransaction.objects.create(
                guide=self.guide,
                amount=self.net_guide_amount,
                transaction_type='credit',
                description=(
                    f"Approbation de la suggestion de {self.client_name} pour le {self.date} | "
                    f"Brut: {self.total_price} TND | "
                    f"Commission ({self.commission_rate}%): -{self.commission_amount} TND | "
                    f"Net: {self.net_guide_amount} TND"
                )
            )

    def __str__(self):
        return f"Suggestion for {self.guide} on {self.date}"


class GuideAvailability(models.Model):
    guide = models.ForeignKey(Guide, on_delete=models.CASCADE, related_name='availability')
    date = models.DateField()
    is_available = models.BooleanField(default=True)

    class Meta:
        unique_together = ('guide', 'date')

    def __str__(self):
        return f"{self.guide} - {self.date} - {'Libre' if self.is_available else 'Occupé'}"


class GuideWalletTransaction(models.Model):
    TYPE_CHOICES = [
        ('credit', 'Crédit'),
        ('debit', 'Débit'),
    ]
    guide = models.ForeignKey(Guide, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=3)
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.guide} - {self.transaction_type} - {self.amount}"
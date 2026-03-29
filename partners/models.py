from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
import uuid, os, secrets, string
from django.core.exceptions import ValidationError


class Partner(models.Model):
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email         = models.EmailField(unique=True)
    company_name  = models.CharField(max_length=255)
    phone         = models.CharField(max_length=20, blank=True)
    logo          = models.ImageField(upload_to='partners/logos/', blank=True, null=True)
    password      = models.CharField(max_length=255)
    is_active     = models.BooleanField(default=True)
    is_verified   = models.BooleanField(default=False)
    account_frozen   = models.BooleanField(default=False)
    # ── Désactivation temporaire ──────────────────────────────────────────────
    is_temporarily_disabled = models.BooleanField(default=False)
    disabled_reason         = models.TextField(blank=True, null=True)
    disabled_at             = models.DateTimeField(blank=True, null=True)
    reactivated_at          = models.DateTimeField(blank=True, null=True)

    CONTRACT_PERIODS = [
        ('1_month',   '1 Mois'),
        ('3_months',  '3 Mois'),
        ('6_months',  '6 Mois'),
        ('10_months', '10 Mois'),
        ('12_months', '12 Mois (1 An)'),
    ]
    PAYMENT_TYPES = [
        ('monthly', 'Paiement Mensuel'),
        ('total',   'Paiement Total'),
    ]

    contract_period = models.CharField(max_length=20, choices=CONTRACT_PERIODS, blank=True, null=True)
    payment_type    = models.CharField(max_length=10, choices=PAYMENT_TYPES, blank=True, null=True)
    contract_start  = models.DateField(blank=True, null=True)
    contract_end    = models.DateField(blank=True, null=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    validated_at    = models.DateTimeField(blank=True, null=True)
    reset_token            = models.CharField(max_length=255, blank=True, null=True)
    reset_token_expires_at = models.DateTimeField(blank=True, null=True)
    pending_email          = models.EmailField(blank=True, null=True)
    konnect_wallet_id      = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name        = 'Partenaire'
        verbose_name_plural = 'Partenaires'
        ordering            = ['-created_at']

    def __str__(self):
        return f"{self.company_name} ({self.email})"

    def set_password(self, raw_password: str):
        self.password = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password(raw_password, self.password)

    def generate_reset_token(self) -> str:
        token = secrets.token_urlsafe(48)
        self.reset_token = token
        self.reset_token_expires_at = timezone.now() + timezone.timedelta(hours=1)
        self.save(update_fields=['reset_token', 'reset_token_expires_at'])
        return token

    def is_reset_token_valid(self, token: str) -> bool:
        if not self.reset_token or not self.reset_token_expires_at:
            return False
        return self.reset_token == token and timezone.now() <= self.reset_token_expires_at

    def clear_reset_token(self):
        self.reset_token = None
        self.reset_token_expires_at = None
        self.save(update_fields=['reset_token', 'reset_token_expires_at'])

    @property
    def is_contract_active(self) -> bool:
        if not self.contract_end:
            return False
        return timezone.now().date() <= self.contract_end

    @property
    def days_until_expiry(self):
        if not self.contract_end:
            return None
        return (self.contract_end - timezone.now().date()).days

    @property
    def can_add_content(self) -> bool:
        return (
            self.is_verified
            and self.is_contract_active
            and not self.account_frozen
            and not self.is_temporarily_disabled
        )

    @property
    def is_accessible(self) -> bool:
        """Compte accessible = actif + non gelé + non désactivé temporairement"""
        return (
            self.is_active
            and not self.account_frozen
            and not self.is_temporarily_disabled
        )


class PartnerContract(models.Model):
    partner        = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name='contracts')
    period         = models.CharField(max_length=20, choices=Partner.CONTRACT_PERIODS)
    payment_type   = models.CharField(max_length=10, choices=Partner.PAYMENT_TYPES)
    start_date     = models.DateField()
    end_date       = models.DateField()
    total_amount   = models.DecimalField(max_digits=10, decimal_places=3)
    monthly_amount = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    is_paid        = models.BooleanField(default=False)
    konnect_payment_ref = models.CharField(max_length=255, blank=True, null=True)
    paid_at        = models.DateTimeField(blank=True, null=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'Contrat Partenaire'
        verbose_name_plural = 'Contrats Partenaires'

    def __str__(self):
        return f"Contrat {self.partner.company_name} — {self.get_period_display()}"

    def mark_as_paid(self, payment_ref: str = None):
        self.is_paid = True
        self.paid_at = timezone.now()
        if payment_ref:
            self.konnect_payment_ref = payment_ref
        self.save(update_fields=['is_paid', 'paid_at', 'konnect_payment_ref'])
        self.partner.contract_start  = self.start_date
        self.partner.contract_end    = self.end_date
        self.partner.contract_period = self.period
        self.partner.payment_type    = self.payment_type
        self.partner.account_frozen  = False
        self.partner.save(update_fields=[
            'contract_start', 'contract_end',
            'contract_period', 'payment_type', 'account_frozen'
        ])


# ── Coupon ────────────────────────────────────────────────────────────────────

def generate_coupon_code():
    """Génère un code coupon unique de 8 caractères."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(8))


class Coupon(models.Model):
    CATEGORY_CHOICES = [
        ('subscription', 'Abonnement'),
        ('content',      'Contenu (Events & Ads)'),
        ('both',         'Les deux'),
    ]

    code               = models.CharField(max_length=20, unique=True, default=generate_coupon_code)
    description        = models.CharField(max_length=255, blank=True)
    discount_percentage = models.PositiveIntegerField(help_text="Pourcentage de réduction (ex: 20 = 20%)")
    category           = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='both')
    is_active          = models.BooleanField(default=True)
    max_uses           = models.PositiveIntegerField(default=0, help_text="0 = illimité")
    current_uses       = models.PositiveIntegerField(default=0)
    expires_at         = models.DateTimeField(blank=True, null=True)
    created_at         = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'Coupon'
        verbose_name_plural = 'Coupons'

    def __str__(self):
        return f"{self.code} — {self.discount_percentage}% ({self.get_category_display()})"

    @property
    def is_valid(self) -> bool:
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        if self.max_uses > 0 and self.current_uses >= self.max_uses:
            return False
        return True

    def apply(self):
        """Incrémente le compteur d'utilisation."""
        self.current_uses += 1
        self.save(update_fields=['current_uses'])


# ── Notification admin ────────────────────────────────────────────────────────

class AdminNotification(models.Model):
    TYPE_CHOICES = [
        ('unpaid_subscription', 'Abonnement impayé'),
        ('unpaid_ad',          'Publicité impayée'),
        ('email_change',       'Changement email en attente'),
        ('new_partner',        'Nouveau partenaire'),
    ]

    partner    = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name='notifications')
    type       = models.CharField(max_length=30, choices=TYPE_CHOICES)
    message    = models.TextField()
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'Notification Admin'
        verbose_name_plural = 'Notifications Admin'

    def __str__(self):
        return f"[{self.get_type_display()}] {self.partner.company_name}"


def validate_image_or_video(value):
    ext = os.path.splitext(value.name)[1].lower()
    allowed = ['.jpg', '.jpeg', '.png', '.webp', '.mp4', '.mov', '.avi']
    if ext not in allowed:
        raise ValidationError(f"Format non supporté. Autorisés : {', '.join(allowed)}")


class PartnerEvent(models.Model):
    STATUS_CHOICES = [
        ('pending',  'En attente de validation'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
        ('boosted',  'Boosté'),
    ]

    partner      = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name='events')

    # ── Titre bilingue ────────────────────────────────────────────────────────
    title        = models.CharField(max_length=255)
    title_en     = models.CharField(
                       max_length=255, blank=True, default='',
                       verbose_name='Titre (Anglais)',
                       help_text="Nom de l'événement en anglais"
                   )
    title_fr     = models.CharField(
                       max_length=255, blank=True, default='',
                       verbose_name='Titre (Français)',
                       help_text="Nom de l'événement en français"
                   )

    # ── Description bilingue ──────────────────────────────────────────────────
    description     = models.TextField()
    description_en  = models.TextField(
                          blank=True, default='',
                          verbose_name='Description (Anglais)',
                          help_text="Description en anglais (HTML autorisé)"
                      )
    description_fr  = models.TextField(
                          blank=True, default='',
                          verbose_name='Description (Français)',
                          help_text="Description en français (HTML autorisé)"
                      )

    # ✅ Category — ForeignKey vers guard.EventCategory (même table que le guard app)
    category     = models.ForeignKey(
                       'guard.EventCategory',
                       on_delete=models.SET_NULL,
                       null=True,
                       blank=True,
                       related_name='partner_events',
                       verbose_name='Catégorie'
                   )

    # ✅ City — ForeignKey vers cities_light.City (même table que guard app)
    city         = models.ForeignKey(
                       'cities_light.City',
                       on_delete=models.SET_NULL,
                       null=True,
                       blank=True,
                       related_name='partner_events',
                       verbose_name='Ville'
                   )

    # ✅ Location — ForeignKey vers guard.Location (même table que guard app)
    location     = models.ForeignKey(
                       'guard.Location',
                       on_delete=models.SET_NULL,
                       null=True,
                       blank=True,
                       related_name='partner_events',
                       verbose_name='Lieu'
                   )

    # ✅ Nouveaux champs Event Details
    event_time   = models.TimeField(
                       blank=True, null=True,
                       verbose_name='Heure de l\'événement'
                   )
    price        = models.DecimalField(
                       max_digits=10, decimal_places=3,
                       default=0,
                       verbose_name='Prix (TND)'
                   )

    start_date   = models.DateField()
    end_date     = models.DateField()
    link         = models.URLField(blank=True, null=True)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_boosted   = models.BooleanField(default=False)
    boosted_at   = models.DateTimeField(blank=True, null=True)
    is_published = models.BooleanField(default=False)
    boost_payment_ref = models.CharField(max_length=255, blank=True, null=True)
    boost_paid_at     = models.DateTimeField(blank=True, null=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'Événement Partenaire'
        verbose_name_plural = 'Événements Partenaires'

    def __str__(self):
        return f"{self.title} — {self.partner.company_name}"

    def get_title(self, lang='en') -> str:
        if lang == 'fr':
            return self.title_fr or self.title_en or self.title
        return self.title_en or self.title_fr or self.title

    def get_description(self, lang='en') -> str:
        if lang == 'fr':
            return self.description_fr or self.description_en or self.description
        return self.description_en or self.description_fr or self.description

    def sync_main_fields(self):
        """
        Synchronise title + description depuis les champs bilingues.
        À appeler dans la view avant event.save().
        """
        if self.title_en:
            self.title = self.title_en
        elif self.title_fr:
            self.title = self.title_fr
        if self.description_en:
            self.description = self.description_en
        elif self.description_fr:
            self.description = self.description_fr

    @property
    def days_until_start(self) -> int:
        if not self.start_date:
            return 0
        return (self.start_date - timezone.now().date()).days

    @property
    def can_be_boosted(self) -> bool:
        return self.days_until_start >= 14

    @property
    def boost_blocked_reason(self) -> str:
        days = self.days_until_start
        if days < 7:
            return f"Début dans {days} jour(s) — minimum 7 jours requis"
        if days < 14:
            return f"Début dans {days} jour(s) — Booster nécessite 14 jours minimum"
        return ""

    @property
    def boost_price(self) -> float:
        from partners.pricing import BOOST_PRICE_PER_DAY
        nb_days = (self.end_date - self.start_date).days + 1
        return round(BOOST_PRICE_PER_DAY * nb_days, 3)


class PartnerEventMedia(models.Model):
    MEDIA_TYPES = [('image', 'Image'), ('video', 'Vidéo')]
    event       = models.ForeignKey(PartnerEvent, on_delete=models.CASCADE, related_name='media')
    file        = models.FileField(upload_to='partners/events/', validators=[validate_image_or_video])
    media_type  = models.CharField(max_length=10, choices=MEDIA_TYPES, default='image')
    order       = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def save(self, *args, **kwargs):
        ext = os.path.splitext(self.file.name)[1].lower()
        self.media_type = 'video' if ext in ['.mp4', '.mov', '.avi'] else 'image'
        super().save(*args, **kwargs)


# ── Validators pour les images publicitaires ──────────────────────────────────

def validate_ad_image(value):
    ext = os.path.splitext(value.name)[1].lower()
    allowed = ['.jpg', '.jpeg', '.png', '.gif']
    if ext not in allowed:
        raise ValidationError("Format non supporté. Autorisés : JPG, PNG, GIF")
    if value.size > 5 * 1024 * 1024:
        raise ValidationError("Fichier trop lourd. Maximum 5MB.")


def validate_mobile_image(value):
    ext = os.path.splitext(value.name)[1].lower()
    allowed = ['.jpg', '.jpeg', '.png', '.gif']
    if ext not in allowed:
        raise ValidationError("Format non supporté. Autorisés : JPG, PNG, GIF")
    if value.size > 5 * 1024 * 1024:
        raise ValidationError("Fichier trop lourd. Maximum 5MB.")


def validate_tablet_image(value):
    ext = os.path.splitext(value.name)[1].lower()
    allowed = ['.jpg', '.jpeg', '.png', '.gif']
    if ext not in allowed:
        raise ValidationError("Format non supporté. Autorisés : JPG, PNG, GIF")
    if value.size > 5 * 1024 * 1024:
        raise ValidationError("Fichier trop lourd. Maximum 5MB.")


class PartnerAd(models.Model):
    STATUS_CHOICES = [
        ('pending',  'En attente'),
        ('approved', 'Approuvée'),
        ('rejected', 'Rejetée'),
        ('active',   'Active'),
        ('expired',  'Expirée'),
    ]

    partner             = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name='ads')
    title               = models.CharField(max_length=255, blank=True, default='')

    mobile_image        = models.ImageField(
                            upload_to='partners/ads/mobile/',
                            validators=[validate_mobile_image],
                            blank=True, null=True,
                            help_text="Taille requise : 320x50 pixels"
                          )
    tablet_image        = models.ImageField(
                            upload_to='partners/ads/tablet/',
                            validators=[validate_tablet_image],
                            blank=True, null=True,
                            help_text="Taille requise : 728x90 pixels"
                          )


    destination_link    = models.URLField(
                            blank=True,
                            default='',
                            help_text="URL de destination. Sera traqué via Short.io."
                          )

    start_date          = models.DateField()
    end_date            = models.DateField()
    price_per_day       = models.DecimalField(max_digits=8, decimal_places=3, default=2.000)
    total_price         = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    is_confirmed        = models.BooleanField(default=False)
    is_paid             = models.BooleanField(default=False)
    konnect_payment_ref = models.CharField(max_length=255, blank=True, null=True)
    paid_at             = models.DateTimeField(blank=True, null=True)
    status              = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    coupon              = models.ForeignKey('Coupon', on_delete=models.SET_NULL, blank=True, null=True)
    discount_applied    = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'Publicité Partenaire'
        verbose_name_plural = 'Publicités Partenaires'

    def __str__(self):
        return f"{self.title or self.auto_title} — {self.partner.company_name}"

    @property
    def auto_title(self) -> str:
        return f"ADS-{str(self.pk)[:6].upper()}" if self.pk else "ADS-XXXXXX"

    def get_display_title(self) -> str:
        return self.title if self.title else self.auto_title

    @property
    def nb_days(self):
        if not self.start_date or not self.end_date:
            return 0
        return (self.end_date - self.start_date).days + 1

    def calculate_price(self):
        base = float(self.price_per_day) * self.nb_days
        if self.discount_applied > 0:
            base = base * (1 - float(self.discount_applied) / 100)
        return round(base, 3)

    def save(self, *args, **kwargs):
        if not self.is_confirmed:
            self.total_price = self.calculate_price()
        super().save(*args, **kwargs)
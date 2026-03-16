from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
import uuid
import os
from django.core.exceptions import ValidationError


class Partner(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    company_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True)
    logo = models.ImageField(upload_to='partners/logos/', blank=True, null=True)
    password = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    account_frozen = models.BooleanField(default=False)

    CONTRACT_PERIODS = [
        ('1_month',   '1 Mois'),
        ('3_months',  '3 Mois'),
        ('6_months',  '6 Mois'),
        ('9_months',  '9 Mois'),
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
    pending_email   = models.EmailField(blank=True, null=True)
    konnect_wallet_id = models.CharField(max_length=255, blank=True, null=True)

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
        import secrets
        token = secrets.token_urlsafe(48)
        self.reset_token = token
        self.reset_token_expires_at = timezone.now() + timezone.timedelta(hours=1)
        self.save(update_fields=['reset_token', 'reset_token_expires_at'])
        return token

    def is_reset_token_valid(self, token: str) -> bool:
        if not self.reset_token or not self.reset_token_expires_at:
            return False
        return (
            self.reset_token == token
            and timezone.now() <= self.reset_token_expires_at
        )

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
        )


class PartnerContract(models.Model):
    partner      = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name='contracts')
    period       = models.CharField(max_length=20, choices=Partner.CONTRACT_PERIODS)
    payment_type = models.CharField(max_length=10, choices=Partner.PAYMENT_TYPES)
    start_date   = models.DateField()
    end_date     = models.DateField()
    total_amount   = models.DecimalField(max_digits=10, decimal_places=3)
    monthly_amount = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    is_paid             = models.BooleanField(default=False)
    konnect_payment_ref = models.CharField(max_length=255, blank=True, null=True)
    paid_at             = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

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

    partner     = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name='events')
    title       = models.CharField(max_length=255)
    description = models.TextField()
    start_date  = models.DateField()
    end_date    = models.DateField()
    link        = models.URLField(blank=True, null=True)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_boosted  = models.BooleanField(default=False)
    boosted_at  = models.DateTimeField(blank=True, null=True)
    is_published = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'Événement Partenaire'
        verbose_name_plural = 'Événements Partenaires'

    def __str__(self):
        return f"{self.title} — {self.partner.company_name}"

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


class PartnerEventMedia(models.Model):
    MEDIA_TYPES = [
        ('image', 'Image'),
        ('video', 'Vidéo'),
    ]
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


def validate_ad_image(value):
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
    partner      = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name='ads')
    title        = models.CharField(max_length=255)
    image        = models.ImageField(upload_to='partners/ads/', validators=[validate_ad_image])
    redirect_url = models.URLField()
    start_date   = models.DateField()
    end_date     = models.DateField()
    price_per_day       = models.DecimalField(max_digits=8, decimal_places=3, default=5.000)
    total_price         = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    is_confirmed        = models.BooleanField(default=False)
    is_paid             = models.BooleanField(default=False)
    konnect_payment_ref = models.CharField(max_length=255, blank=True, null=True)
    paid_at             = models.DateTimeField(blank=True, null=True)
    status              = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'Publicité Partenaire'
        verbose_name_plural = 'Publicités Partenaires'

    def __str__(self):
        return f"{self.title} — {self.partner.company_name}"

    @property
    def nb_days(self):
        if not self.start_date or not self.end_date:
            return 0
        return (self.end_date - self.start_date).days + 1

    def calculate_price(self):
        return round(float(self.price_per_day) * self.nb_days, 3)

    def save(self, *args, **kwargs):
        if not self.is_confirmed:
            self.total_price = self.calculate_price()
        super().save(*args, **kwargs)
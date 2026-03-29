from django.contrib import admin
from django.utils import timezone
from django.contrib import messages
from django.utils.html import format_html
from partners.models import (
    Partner, PartnerContract, PartnerEvent,
    PartnerEventMedia, PartnerAd, Coupon, AdminNotification
)


# ── Actions ───────────────────────────────────────────────────────────────────

def approve_email_change(modeladmin, request, queryset):
    count = 0
    for partner in queryset.filter(pending_email__isnull=False):
        partner.email = partner.pending_email
        partner.pending_email = None
        partner.save(update_fields=['email', 'pending_email'])
        count += 1
    messages.success(request, f"{count} changement(s) d'email approuvé(s).")
approve_email_change.short_description = "✅ Approuver le changement d'email"


def reject_email_change(modeladmin, request, queryset):
    count = queryset.filter(pending_email__isnull=False).update(pending_email=None)
    messages.success(request, f"{count} changement(s) rejeté(s).")
reject_email_change.short_description = "❌ Rejeter le changement d'email"


def freeze_account(modeladmin, request, queryset):
    count = queryset.update(account_frozen=True)
    messages.success(request, f"{count} compte(s) suspendu(s).")
freeze_account.short_description = "🔒 Suspendre le compte"


def unfreeze_account(modeladmin, request, queryset):
    count = queryset.update(account_frozen=False)
    messages.success(request, f"{count} compte(s) réactivé(s).")
unfreeze_account.short_description = "🔓 Réactiver le compte"


def verify_partner(modeladmin, request, queryset):
    count = queryset.update(is_verified=True, validated_at=timezone.now())
    messages.success(request, f"{count} partenaire(s) vérifié(s).")
verify_partner.short_description = "✅ Vérifier le partenaire"


def disable_temporarily(modeladmin, request, queryset):
    count = queryset.update(
        is_temporarily_disabled=True,
        disabled_at=timezone.now(),
        disabled_reason="Désactivé par l'admin"
    )
    messages.warning(request, f"{count} compte(s) désactivé(s) temporairement.")
disable_temporarily.short_description = "⏸ Désactiver temporairement"


def reactivate_account(modeladmin, request, queryset):
    count = queryset.update(
        is_temporarily_disabled=False,
        reactivated_at=timezone.now(),
        disabled_reason=None
    )
    messages.success(request, f"{count} compte(s) réactivé(s).")
reactivate_account.short_description = "▶️ Réactiver le compte"


# ── Admin Partner ─────────────────────────────────────────────────────────────

@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display  = [
        'company_name', 'email', 'status_display',
        'contract_end', 'days_left_display',
        'pending_email_display', 'unpaid_alert_display'
    ]
    list_filter   = ['is_verified', 'is_active', 'account_frozen',
                     'is_temporarily_disabled', 'contract_period']
    search_fields = ['company_name', 'email', 'pending_email']
    readonly_fields = ['created_at', 'validated_at', 'id', 'disabled_at', 'reactivated_at']
    actions = [
        verify_partner, approve_email_change, reject_email_change,
        freeze_account, unfreeze_account,
        disable_temporarily, reactivate_account,
    ]

    fieldsets = (
        ('Identité', {
            'fields': ('id', 'company_name', 'email', 'phone', 'logo', 'password')
        }),
        ('Statut', {
            'fields': ('is_active', 'is_verified', 'account_frozen',
                       'is_temporarily_disabled', 'disabled_reason',
                       'disabled_at', 'reactivated_at', 'validated_at')
        }),
        ('Contrat', {
            'fields': ('contract_period', 'payment_type', 'contract_start', 'contract_end')
        }),
        ('Email en attente', {
            'fields': ('pending_email',),
            'classes': ('collapse',),
        }),
        ('Konnect', {
            'fields': ('konnect_wallet_id',),
            'classes': ('collapse',),
        }),
        ('Dates', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        """Hash automatiquement le mot de passe si modifié depuis l'admin."""
        raw = form.cleaned_data.get('password', '')
        if raw and not raw.startswith('pbkdf2_'):
            obj.set_password(raw)
        super().save_model(request, obj, form, change)

    def status_display(self, obj):
        if obj.is_temporarily_disabled:
            return format_html('<span style="color:orange">⏸ Désactivé</span>')
        if obj.account_frozen:
            return format_html('<span style="color:red">🔒 Suspendu</span>')
        if obj.is_verified:
            return format_html('<span style="color:green">✅ Actif</span>')
        return format_html('<span style="color:gray">⏳ En attente</span>')
    status_display.short_description = "Statut"

    def days_left_display(self, obj):
        days = obj.days_until_expiry
        if days is None:
            return "—"
        if days <= 0:
            return format_html('<span style="color:red">Expiré</span>')
        if days <= 7:
            return format_html('<span style="color:orange">{} jours</span>', days)
        return f"{days} jours"
    days_left_display.short_description = "Expiration"

    def pending_email_display(self, obj):
        if obj.pending_email:
            return format_html('<span style="color:orange">⏳ {}</span>', obj.pending_email)
        return "—"
    pending_email_display.short_description = "Email en attente"

    def unpaid_alert_display(self, obj):
        days = obj.days_until_expiry
        if days is not None and days <= -10:
            return format_html(
                '<span style="color:red;font-weight:bold">🚨 Impayé {}j</span>',
                abs(days)
            )
        return "—"
    unpaid_alert_display.short_description = "⚠️ Alerte impayé"


# ── Admin Contract ─────────────────────────────────────────────────────────────

@admin.register(PartnerContract)
class PartnerContractAdmin(admin.ModelAdmin):
    list_display    = ['partner', 'period', 'payment_type', 'start_date',
                       'end_date', 'is_paid', 'total_amount']
    list_filter     = ['is_paid', 'period', 'payment_type']
    search_fields   = ['partner__company_name', 'partner__email']
    readonly_fields = ['created_at', 'paid_at']


# ── Admin Event ────────────────────────────────────────────────────────────────

def approve_event(modeladmin, request, queryset):
    count = queryset.update(status='approved', is_published=True)
    messages.success(request, f"{count} événement(s) approuvé(s).")
approve_event.short_description = "✅ Approuver"


def reject_event(modeladmin, request, queryset):
    count = queryset.update(status='rejected', is_published=False)
    messages.success(request, f"{count} événement(s) rejeté(s).")
reject_event.short_description = "❌ Rejeter"


@admin.register(PartnerEvent)
class PartnerEventAdmin(admin.ModelAdmin):
    list_display    = ['title', 'partner', 'status', 'start_date',
                       'end_date', 'is_boosted', 'is_published']
    list_filter     = ['status', 'is_boosted', 'is_published']
    search_fields   = ['title', 'partner__company_name']
    actions         = [approve_event, reject_event]
    readonly_fields = ['created_at', 'updated_at', 'boosted_at']


# ── Admin Ad ───────────────────────────────────────────────────────────────────

def approve_ad(modeladmin, request, queryset):
    count = queryset.update(status='active')
    messages.success(request, f"{count} publicité(s) approuvée(s).")
approve_ad.short_description = "✅ Approuver"


@admin.register(PartnerAd)
class PartnerAdAdmin(admin.ModelAdmin):
    list_display    = ['title', 'partner', 'status', 'start_date',
                       'end_date', 'total_price', 'is_paid', 'coupon']
    list_filter     = ['status', 'is_paid', 'is_confirmed']
    search_fields   = ['title', 'partner__company_name']
    actions         = [approve_ad]
    readonly_fields = ['created_at', 'updated_at', 'paid_at', 'total_price']


# ── Admin Coupon ───────────────────────────────────────────────────────────────

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display  = [
        'code', 'discount_percentage', 'category',
        'is_active', 'current_uses', 'max_uses',
        'expires_at', 'validity_display'
    ]
    list_filter     = ['is_active', 'category']
    search_fields   = ['code', 'description']
    readonly_fields = ['created_at', 'current_uses', 'code']

    fieldsets = (
        ('Code', {
            'fields': ('code', 'description')
        }),
        ('Réduction', {
            'fields': ('discount_percentage', 'category')
        }),
        ('Limites', {
            'fields': ('is_active', 'max_uses', 'current_uses', 'expires_at')
        }),
        ('Dates', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    def validity_display(self, obj):
        if obj.is_valid:
            return format_html('<span style="color:green">✅ Valide</span>')
        return format_html('<span style="color:red">❌ Invalide</span>')
    validity_display.short_description = "Validité"


# ── Admin Notification ─────────────────────────────────────────────────────────

def mark_read(modeladmin, request, queryset):
    queryset.update(is_read=True)
    messages.success(request, "Notifications marquées comme lues.")
mark_read.short_description = "✅ Marquer comme lu"


@admin.register(AdminNotification)
class AdminNotificationAdmin(admin.ModelAdmin):
    list_display    = ['partner', 'type', 'message', 'is_read', 'created_at']
    list_filter     = ['is_read', 'type']
    search_fields   = ['partner__company_name', 'message']
    readonly_fields = ['created_at']
    actions         = [mark_read]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('is_read', '-created_at')
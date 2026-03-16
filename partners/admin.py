from django.contrib import admin
from django.utils import timezone
from django.contrib import messages
from partners.models import Partner, PartnerContract, PartnerEvent, PartnerEventMedia, PartnerAd


# ── Actions admin ─────────────────────────────────────────────────────────────

def approve_email_change(modeladmin, request, queryset):
    count = 0
    for partner in queryset.filter(pending_email__isnull=False):
        partner.email         = partner.pending_email
        partner.pending_email = None
        partner.save(update_fields=['email', 'pending_email'])
        count += 1
    messages.success(request, f"{count} changement(s) d'email approuvé(s).")
approve_email_change.short_description = "✅ Approuver le changement d'email"


def reject_email_change(modeladmin, request, queryset):
    count = queryset.filter(pending_email__isnull=False).update(pending_email=None)
    messages.success(request, f"{count} changement(s) d'email rejeté(s).")
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


# ── Admin Partner ─────────────────────────────────────────────────────────────

@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display  = ['company_name', 'email', 'is_verified', 'is_active',
                     'account_frozen', 'contract_end', 'pending_email_display']
    list_filter   = ['is_verified', 'is_active', 'account_frozen', 'contract_period']
    search_fields = ['company_name', 'email', 'pending_email']
    readonly_fields = ['created_at', 'validated_at', 'id']
    actions = [verify_partner, approve_email_change, reject_email_change,
               freeze_account, unfreeze_account]

    fieldsets = (
        ('Identité', {
            'fields': ('id', 'company_name', 'email', 'phone', 'logo', 'password')
        }),
        ('Statut', {
            'fields': ('is_active', 'is_verified', 'account_frozen', 'validated_at')
        }),
        ('Contrat', {
            'fields': ('contract_period', 'payment_type', 'contract_start', 'contract_end')
        }),
        ('Changement email en attente', {
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

    def pending_email_display(self, obj):
        if obj.pending_email:
            return f"⏳ {obj.pending_email}"
        return "—"
    pending_email_display.short_description = "Email en attente"


# ── Admin Contract ────────────────────────────────────────────────────────────

@admin.register(PartnerContract)
class PartnerContractAdmin(admin.ModelAdmin):
    list_display  = ['partner', 'period', 'payment_type', 'start_date', 'end_date', 'is_paid', 'total_amount']
    list_filter   = ['is_paid', 'period', 'payment_type']
    search_fields = ['partner__company_name', 'partner__email']
    readonly_fields = ['created_at', 'paid_at']


# ── Admin Event ───────────────────────────────────────────────────────────────

def approve_event(modeladmin, request, queryset):
    count = queryset.update(status='approved', is_published=True)
    messages.success(request, f"{count} événement(s) approuvé(s).")
approve_event.short_description = "✅ Approuver les événements"


def reject_event(modeladmin, request, queryset):
    count = queryset.update(status='rejected', is_published=False)
    messages.success(request, f"{count} événement(s) rejeté(s).")
reject_event.short_description = "❌ Rejeter les événements"


@admin.register(PartnerEvent)
class PartnerEventAdmin(admin.ModelAdmin):
    list_display  = ['title', 'partner', 'status', 'start_date', 'end_date', 'is_boosted', 'is_published']
    list_filter   = ['status', 'is_boosted', 'is_published']
    search_fields = ['title', 'partner__company_name']
    actions       = [approve_event, reject_event]
    readonly_fields = ['created_at', 'updated_at', 'boosted_at']


# ── Admin Ad ──────────────────────────────────────────────────────────────────

def approve_ad(modeladmin, request, queryset):
    count = queryset.update(status='active')
    messages.success(request, f"{count} publicité(s) approuvée(s).")
approve_ad.short_description = "✅ Approuver les publicités"


@admin.register(PartnerAd)
class PartnerAdAdmin(admin.ModelAdmin):
    list_display  = ['title', 'partner', 'status', 'start_date', 'end_date', 'total_price', 'is_paid']
    list_filter   = ['status', 'is_paid', 'is_confirmed']
    search_fields = ['title', 'partner__company_name']
    actions       = [approve_ad]
    readonly_fields = ['created_at', 'updated_at', 'paid_at', 'total_price']
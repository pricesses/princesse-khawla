from django.contrib import admin
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from .models import Guide, GuideReview, GuideSuggestion, GuideAvailability, GuideWalletTransaction, GuideAdminRating
from .email_utils import send_guide_welcome_email


class GuideReviewInline(admin.TabularInline):
    model = GuideReview
    extra = 0
    readonly_fields = ['created_at']


class GuideSuggestionInline(admin.TabularInline):
    model = GuideSuggestion
    extra = 0
    readonly_fields = ['total_price', 'created_at']


class GuideAdminRatingInline(admin.StackedInline):
    """
    Permet à l'admin de saisir/modifier sa note directement
    depuis la fiche du guide.
    """
    model = GuideAdminRating
    extra = 1          # Crée le formulaire s'il n'existe pas encore
    max_num = 1        # Un seul enregistrement par guide
    can_delete = False
    verbose_name = "Évaluation Administrateur"
    verbose_name_plural = "Évaluation Administrateur"
    fields = ['rating', 'comment', 'updated_by']
    readonly_fields = ['updated_at'] if hasattr(GuideAdminRating, 'updated_at') else []

    def save_model(self, request, obj, form, change):
        # Enregistre automatiquement qui a modifié la note
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Guide)
class GuideAdmin(admin.ModelAdmin):
    list_display = ['get_name', 'email', 'client_stars', 'admin_stars', 'stars', 'wallet_balance', 'created_at']
    search_fields = ['user__first_name', 'user__last_name', 'email']
    inlines = [GuideAdminRatingInline, GuideReviewInline, GuideSuggestionInline]

    fieldsets = (
        ('Informations de base', {
            'fields': ('user', 'email', 'phone', 'photo')
        }),
        ('Profil', {
            'fields': ('description', 'languages', 'accepts_children', 'price_adult', 'price_child')
        }),
        ('Finances', {
            'fields': ('wallet_balance',)
        }),
        ('Notes & Évaluations', {
            'fields': ('client_stars', 'admin_stars', 'stars'),
            'description': (
                "• client_stars : moyenne automatique des avis clients (lecture seule).\n"
                "• admin_stars  : définie via le bloc « Évaluation Administrateur » ci-dessous.\n"
                "• stars        : moyenne pondérée globale (60 % clients / 40 % admin)."
            ),
        }),
        ('Système', {
            'fields': ('pending_email', 'email_change_token', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['client_stars', 'admin_stars', 'stars', 'created_at', 'updated_at']

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    get_name.short_description = "Nom du Guide"

    def save_model(self, request, obj, form, change):
        if not change:  # Création d'un nouveau guide
            if not obj.user_id:
                password = get_random_string(10)
                username = obj.email
                user = User.objects.create_user(username=username, email=obj.email, password=password)
                obj.user = user
                send_guide_welcome_email(obj, password)

            if not obj.email and obj.user.email:
                obj.email = obj.user.email

        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        """Injecte automatiquement updated_by sur les GuideAdminRating sauvegardés via inline."""
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, GuideAdminRating):
                instance.updated_by = request.user
            instance.save()
        formset.save_m2m()


@admin.register(GuideAdminRating)
class GuideAdminRatingAdmin(admin.ModelAdmin):
    """Vue dédiée pour gérer les évaluations admin (accessible aussi en liste)."""
    list_display = ['guide', 'rating', 'updated_by', 'updated_at']
    list_filter = ['rating', 'updated_at']
    readonly_fields = ['updated_at']
    fields = ['guide', 'rating', 'comment', 'updated_by', 'updated_at']

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(GuideReview)
class GuideReviewAdmin(admin.ModelAdmin):
    list_display = ['guide', 'client_name', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']


@admin.register(GuideSuggestion)
class GuideSuggestionAdmin(admin.ModelAdmin):
    list_display = ['guide', 'client_name', 'date', 'status', 'total_price']
    list_filter = ['status', 'date']
    actions = ['approve_suggestions']

    def approve_suggestions(self, request, queryset):
        for suggestion in queryset:
            suggestion.approve()
        self.message_user(request, f"{queryset.count()} suggestions approuvées.")
    approve_suggestions.short_description = "Approuver les suggestions sélectionnées"


@admin.register(GuideAvailability)
class GuideAvailabilityAdmin(admin.ModelAdmin):
    list_display = ['guide', 'date', 'is_available']
    list_filter = ['is_available', 'date']


@admin.register(GuideWalletTransaction)
class GuideWalletTransactionAdmin(admin.ModelAdmin):
    list_display = ['guide', 'amount', 'transaction_type', 'created_at']
    list_filter = ['transaction_type', 'created_at']
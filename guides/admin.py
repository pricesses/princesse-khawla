from django.contrib import admin
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from .models import Guide, GuideReview, GuideSuggestion, GuideAvailability, GuideWalletTransaction
from .email_utils import send_guide_welcome_email

class GuideReviewInline(admin.TabularInline):
    model = GuideReview
    extra = 0

class GuideSuggestionInline(admin.TabularInline):
    model = GuideSuggestion
    extra = 0
    readonly_fields = ['total_price', 'created_at']

@admin.register(Guide)
class GuideAdmin(admin.ModelAdmin):
    list_display = ['get_name', 'email', 'stars', 'wallet_balance', 'created_at']
    search_fields = ['user__first_name', 'user__last_name', 'email']
    inlines = [GuideReviewInline, GuideSuggestionInline]
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('user', 'email', 'phone', 'photo', 'stars')
        }),
        ('Profil', {
            'fields': ('description', 'languages', 'accepts_children', 'price_adult', 'price_child')
        }),
        ('Finances', {
            'fields': ('wallet_balance',)
        }),
        ('Système', {
            'fields': ('pending_email', 'email_change_token', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    get_name.short_description = "Nom du Guide"

    def save_model(self, request, obj, form, change):
        if not change: # Creating a new Guide
            # If user is not selected, create one
            if not obj.user_id:
                password = get_random_string(10)
                username = obj.email
                user = User.objects.create_user(username=username, email=obj.email, password=password)
                obj.user = user
                
                # Send welcome email
                send_guide_welcome_email(obj, password)
            
            # Ensure email is synced with user email
            if not obj.email and obj.user.email:
                obj.email = obj.user.email
        
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

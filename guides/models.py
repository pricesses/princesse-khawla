from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
import secrets

class Guide(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='guide_profile')
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to='guides/photos/', null=True, blank=True) # User said mandatory, will validate in form
    description = models.TextField(blank=True)
    languages = models.CharField(max_length=255, blank=True) # e.g., "Français, Anglais"
    accepts_children = models.BooleanField(default=True)
    
    price_adult = models.DecimalField(max_digits=10, decimal_places=3, default=0.000)
    price_child = models.DecimalField(max_digits=10, decimal_places=3, default=0.000)
    
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=3, default=0.000)
    stars = models.FloatField(default=0.0) # Admin can set initially, then average of reviews
    
    # Email change fields
    pending_email = models.EmailField(blank=True, null=True)
    email_change_token = models.CharField(max_length=64, blank=True, default='')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Guide: {self.user.get_full_name() or self.user.username} ({self.email})"

    def update_stars(self):
        reviews = self.reviews.all()
        if reviews.exists():
            avg = reviews.aggregate(models.Avg('rating'))['rating__avg']
            self.stars = round(avg, 1)
            self.save(update_fields=['stars'])

class GuideReview(models.Model):
    guide = models.ForeignKey(Guide, on_delete=models.CASCADE, related_name='reviews')
    client_name = models.CharField(max_length=255)
    rating = models.PositiveIntegerField(default=5) # 1-5
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.guide.update_stars()

    def __str__(self):
        return f"Review for {self.guide} by {self.client_name}"

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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)

    def calculate_total(self):
        # Children under 6 are free
        # Children over 6 pay guide's child price (or adult price if not specified)
        # Adults pay guide's adult price
        price = (self.nb_adults * self.guide.price_adult) + (self.nb_children_over_6 * self.guide.price_child)
        self.total_price = price
        return price

    def approve(self):
        if self.status != 'approved':
            self.status = 'approved'
            self.calculate_total()
            self.save()
            
            # Update guide wallet balance
            self.guide.wallet_balance += self.total_price
            self.guide.save(update_fields=['wallet_balance'])
            
            # Add to calendar/availability
            GuideAvailability.objects.get_or_create(guide=self.guide, date=self.date, is_available=False)
            
            # Create wallet transaction
            GuideWalletTransaction.objects.create(
                guide=self.guide,
                amount=self.total_price,
                transaction_type='credit',
                description=f"Approbation de la suggestion de {self.client_name} pour le {self.date}"
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

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Guide, GuideSuggestion, GuideReview, GuideAvailability
from .forms import GuideSettingsForm
from .email_utils import send_guide_email_change_confirmation


@login_required
def guide_dashboard(request):
    guide = get_object_or_404(Guide, user=request.user)
    suggestions_pending = guide.suggestions.filter(status='pending').order_by('-created_at')[:5]
    recent_reviews = guide.reviews.order_by('-created_at')[:5]
    import json
    booked = {}
    for s in guide.suggestions.exclude(status='rejected'):
        booked[s.date.strftime('%Y-%m-%d')] = {
            'status': s.status,
            'client': s.client_name,
            'adults': s.nb_adults,
            'children': s.nb_children_over_6 + s.nb_children_under_6,
        }
    context = {
        'guide': guide,
        'suggestions_pending': suggestions_pending,
        'recent_reviews': recent_reviews,
        'booked_dates_json': json.dumps(booked),
    }
    return render(request, 'guides/dashboard.html', context)

@login_required
def guide_settings(request):
    guide = get_object_or_404(Guide, user=request.user)
    if request.method == 'POST':
        form = GuideSettingsForm(request.POST, request.FILES, instance=guide)
        if form.is_valid():
            new_email = form.cleaned_data.get('email')
            
            # Save other fields
            form.save()
            
            # Sync first/last name
            guide.user.first_name = form.cleaned_data.get('first_name')
            guide.user.last_name = form.cleaned_data.get('last_name')
            guide.user.save()
            
            # Handle email change
            if new_email and new_email != guide.email:
                send_guide_email_change_confirmation(guide, new_email)
                messages.info(request, f"Un email de confirmation a été envoyé à {new_email}. Le changement sera effectif après confirmation.")
            
            messages.success(request, "Profil mis à jour avec succès.")
            return redirect('guide_settings')
    else:
        form = GuideSettingsForm(instance=guide)
    
    return render(request, 'guides/settings.html', {'form': form, 'guide': guide})

@login_required
def guide_suggestions(request):
    guide = get_object_or_404(Guide, user=request.user)
    suggestions = guide.suggestions.all().order_by('-date')
    return render(request, 'guides/suggestions.html', {'suggestions': suggestions, 'guide': guide})

@login_required
def approve_suggestion(request, pk):
    suggestion = get_object_or_404(GuideSuggestion, pk=pk, guide__user=request.user)
    if suggestion.status == 'pending':
        suggestion.approve()
        messages.success(request, f"Suggestion du {suggestion.date} approuvée. Votre portefeuille a été crédité.")
    return redirect('guide_suggestions')

@login_required
def reject_suggestion(request, pk):
    suggestion = get_object_or_404(GuideSuggestion, pk=pk, guide__user=request.user)
    if suggestion.status == 'pending':
        suggestion.status = 'rejected'
        suggestion.save()
        messages.warning(request, f"Suggestion du {suggestion.date} rejetée.")
    return redirect('guide_suggestions')

@login_required
def guide_reviews(request):
    guide = get_object_or_404(Guide, user=request.user)
    reviews = guide.reviews.all().order_by('-created_at')
    return render(request, 'guides/reviews.html', {'reviews': reviews, 'guide': guide})

def verify_email_change(request, token):
    guide = get_object_or_404(Guide, email_change_token=token)
    if guide.pending_email:
        old_email = guide.email
        new_email = guide.pending_email
        
        # Update email
        guide.email = new_email
        guide.user.email = new_email
        guide.user.username = new_email # Assuming username is email
        guide.user.save()
        
        guide.pending_email = None
        guide.email_change_token = ''
        guide.save()
        
        messages.success(request, f"Votre email a été mis à jour avec succès : {new_email}")
        return redirect('guide_settings')
    
    messages.error(request, "Lien de confirmation invalide ou expiré.")
    return redirect('guide_dashboard')

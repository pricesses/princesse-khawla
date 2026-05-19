from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal
from django.utils.translation import gettext as _
from .models import Guide, GuideSuggestion, GuideReview, GuideAvailability
from .forms import GuideSettingsForm
from .email_utils import send_guide_email_change_confirmation



@login_required
def guide_dashboard(request):
    guide = get_object_or_404(Guide, user=request.user)
    
    # Auto-synchronize the preferred language with the current active dashboard locale
    from django.utils import translation
    current_lang = translation.get_language()
    if current_lang in ['fr', 'en'] and guide.preferred_language != current_lang:
        guide.preferred_language = current_lang
        guide.save(update_fields=['preferred_language'])

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

    # Financial summary (approved suggestions only)
    approved = list(guide.suggestions.filter(status='approved'))
    total_brut       = sum(s.total_price       for s in approved) or Decimal('0')
    total_commission = sum(s.commission_amount  for s in approved)
    total_net        = sum(s.net_guide_amount   for s in approved)

    # --- Note clients (moyenne des GuideReview) ---
    client_stars = guide.client_stars

    # --- Note admin (depuis GuideAdminRating si elle existe) ---
    try:
        admin_rating_obj = guide.admin_rating
        admin_stars      = admin_rating_obj.rating
        admin_comment    = admin_rating_obj.comment  # commentaire interne (non affiché au guide)
    except Exception:
        admin_stars   = guide.admin_stars   # fallback sur le champ du modèle
        admin_comment = ""

    # --- Note globale pondérée ---
    global_stars = guide.stars

    context = {
        'guide': guide,
        'suggestions_pending': suggestions_pending,
        'recent_reviews': recent_reviews,
        'booked_dates_json': json.dumps(booked),
        'total_brut': total_brut,
        'total_commission': total_commission,
        'total_net': total_net,
        # Nouvelles variables de notation
        'client_stars': client_stars,
        'admin_stars': admin_stars,
        'global_stars': global_stars,
    }
    return render(request, 'guides/dashboard.html', context)


@login_required
def guide_settings(request):
    guide = get_object_or_404(Guide, user=request.user)

    # Auto-synchronize the preferred language with the current active dashboard locale
    from django.utils import translation
    current_lang = translation.get_language()
    if current_lang in ['fr', 'en'] and guide.preferred_language != current_lang:
        guide.preferred_language = current_lang
        guide.save(update_fields=['preferred_language'])
    if request.method == 'POST':
        form = GuideSettingsForm(request.POST, request.FILES, instance=guide)
        if form.is_valid():
            new_email = form.cleaned_data.get('email')

            form.save()

            guide.user.first_name = form.cleaned_data.get('first_name')
            guide.user.last_name  = form.cleaned_data.get('last_name')
            guide.user.save()

            if new_email and new_email != guide.email:
                send_guide_email_change_confirmation(guide, new_email)
                messages.info(
                    request,
                    _("Un email de confirmation a été envoyé à {new_email}. Le changement sera effectif après confirmation.").format(new_email=new_email)
                )

            messages.success(request, _("Profil mis à jour avec succès."))
            return redirect('guide_settings')
    else:
        form = GuideSettingsForm(instance=guide)

    return render(request, 'guides/settings.html', {'form': form, 'guide': guide})


@login_required
def guide_suggestions(request):
    guide = get_object_or_404(Guide, user=request.user)
    suggestions = guide.suggestions.exclude(status='rejected').order_by('-date')
    return render(request, 'guides/suggestions.html', {'suggestions': suggestions, 'guide': guide})


@login_required
def approve_suggestion(request, pk):
    suggestion = get_object_or_404(GuideSuggestion, pk=pk, guide__user=request.user)
    if suggestion.status == 'pending':
        suggestion.approve()
        messages.success(
            request,
            _("Suggestion du {date} approuvée. Votre portefeuille a été crédité.").format(date=suggestion.date)
        )
    return redirect('guide_suggestions')


@login_required
def reject_suggestion(request, pk):
    suggestion = get_object_or_404(GuideSuggestion, pk=pk, guide__user=request.user)
    if suggestion.status == 'pending':
        suggestion.status = 'rejected'
        suggestion.save()
        messages.warning(request, _("Suggestion du {date} rejetée.").format(date=suggestion.date))
    return redirect('guide_suggestions')


@login_required
def guide_reviews(request):
    guide = get_object_or_404(Guide, user=request.user)
    reviews = guide.reviews.all().order_by('-created_at')
    return render(request, 'guides/reviews.html', {'reviews': reviews, 'guide': guide})


def verify_email_change(request, token):
    guide = get_object_or_404(Guide, email_change_token=token)
    if guide.pending_email:
        new_email = guide.pending_email

        guide.email        = new_email
        guide.user.email   = new_email
        guide.user.username = new_email
        guide.user.save()

        guide.pending_email      = None
        guide.email_change_token = ''
        guide.save()

        messages.success(request, _("Votre email a été mis à jour avec succès : {new_email}").format(new_email=new_email))
        return redirect('guide_settings')

    messages.error(request, _("Lien de confirmation invalide ou expiré."))
    return redirect('guide_dashboard')
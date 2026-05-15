import secrets
import os
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.translation import gettext as _
from django.conf import settings
from email.mime.image import MIMEImage

def send_guide_welcome_email(guide, password):
    """
    Sends credentials to the new guide.
    """
    subject = _("Bienvenue sur FielMedina - Vos identifiants Guide")
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@fielmedina.com')
    to_email = [guide.email]

    context = {
        'guide_name': guide.user.get_full_name() or guide.user.username,
        'username': guide.user.username,
        'email': guide.email,
        'password': password,
        'login_url': f"{getattr(settings, 'SITE_URL', 'http://localhost:8000')}/auth/login/",
        'company_name': 'FielMedina',
    }

    html_content = render_to_string('guides/emails/welcome_guide.html', context)
    text_content = f"Bonjour {context['guide_name']},\n\nVotre compte guide a été créé.\nEmail: {context['email']}\nMot de passe: {context['password']}\nConnectez-vous ici: {context['login_url']}"

    msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
    msg.mixed_subtype = 'related'  # Required for CID logo images to show in Gmail
    msg.attach_alternative(html_content, "text/html")
    
    # Attach icons if they exist
    icon_map = {
        'logo_img': 'icon.png',
        'user_icon': 'email_user.png',
        'lock_icon': 'email_lock.png',
        'alert_icon': 'email_alert.png'
    }
    
    for cid, filename in icon_map.items():
        icon_path = os.path.join(settings.BASE_DIR, 'static', filename)
        if os.path.exists(icon_path):
            with open(icon_path, 'rb') as f:
                img = MIMEImage(f.read())
                img.add_header('Content-ID', f'<{cid}>')
                img.add_header('Content-Disposition', 'inline', filename=filename)
                msg.attach(img)

    msg.send(fail_silently=False)

def send_new_suggestion_email(guide, suggestion):
    """
    Notifie le guide par e-mail d'une nouvelle demande.
    La langue de l'email suit guide.preferred_language ('fr' ou 'en').
    """
    lang = getattr(guide, 'preferred_language', 'fr')
    with translation.override(lang):
        _send_new_suggestion_email_inner(guide, suggestion)


def _send_new_suggestion_email_inner(guide, suggestion):
    guide_name  = guide.user.get_full_name() or guide.user.username
    site_url    = getattr(settings, 'SITE_URL', 'http://localhost:8000')
    commission  = suggestion.commission_rate

    adults_subtotal   = round(suggestion.nb_adults * float(guide.price_adult), 3)
    children_subtotal = round(suggestion.nb_children_over_6 * float(guide.price_child), 3)
    total_price       = round(float(suggestion.total_price) if float(suggestion.total_price) > 0
                              else adults_subtotal + children_subtotal, 3)
    net_amount        = round(total_price * (1 - float(commission) / 100), 3)

    lang = getattr(guide, 'preferred_language', 'fr')

    if lang == 'en':
        subject    = "🔔 New Booking Request — FielMedina"
        text_intro = f"Hello {guide_name},\n\nYou have received a new tour booking request.\n\n"
        text_body  = (
            f"Client  : {suggestion.client_name} ({suggestion.client_email})\n"
            f"Date    : {suggestion.date.strftime('%d/%m/%Y')}\n"
            f"Group   : {suggestion.nb_adults} adult(s)"
            f"{f', {suggestion.nb_children_over_6} child(ren) >6 yrs' if suggestion.nb_children_over_6 else ''}"
            f"{f', {suggestion.nb_children_under_6} child(ren) <6 yrs' if suggestion.nb_children_under_6 else ''}\n"
            f"Amount  : {total_price:.3f} TND (net: {net_amount:.3f} TND)\n\n"
            f"View your dashboard: {site_url}/guides/suggestions/"
        )
    else:
        subject    = "🔔 Nouvelle demande de réservation — FielMedina"
        text_intro = f"Bonjour {guide_name},\n\nVous avez reçu une nouvelle demande de réservation.\n\n"
        text_body  = (
            f"Client  : {suggestion.client_name} ({suggestion.client_email})\n"
            f"Date    : {suggestion.date.strftime('%d/%m/%Y')}\n"
            f"Groupe  : {suggestion.nb_adults} adulte(s)"
            f"{f', {suggestion.nb_children_over_6} enfant(s) >6 ans' if suggestion.nb_children_over_6 else ''}"
            f"{f', {suggestion.nb_children_under_6} enfant(s) <6 ans' if suggestion.nb_children_under_6 else ''}\n"
            f"Montant : {total_price:.3f} TND (net : {net_amount:.3f} TND)\n\n"
            f"Consultez votre tableau de bord : {site_url}/guides/suggestions/"
        )

    context = {
        'guide_name':                     guide_name,
        'lang':                           lang,
        'suggestion_client_name':         suggestion.client_name,
        'suggestion_client_email':        suggestion.client_email,
        'suggestion_date':                suggestion.date.strftime('%d/%m/%Y'),
        'suggestion_nb_adults':           suggestion.nb_adults,
        'suggestion_nb_children_over_6':  suggestion.nb_children_over_6,
        'suggestion_nb_children_under_6': suggestion.nb_children_under_6,
        'suggestion_message':             suggestion.message,
        'price_adult':                    f"{float(guide.price_adult):.3f}",
        'price_child':                    f"{float(guide.price_child):.3f}",
        'adults_subtotal':                f"{adults_subtotal:.3f}",
        'children_subtotal':              f"{children_subtotal:.3f}",
        'suggestion_total_price':         f"{total_price:.3f}",
        'commission_rate':                commission,
        'net_amount':                     f"{net_amount:.3f}",
        'dashboard_url':                  f"{site_url}/guides/suggestions/",
        'company_name':                   'FielMedina',
    }

    from_email   = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@fielmedina.com')
    html_content = render_to_string('guides/emails/new_suggestion_notify.html', context)
    text_content = text_intro + text_body

    msg = EmailMultiAlternatives(subject, text_content, from_email, [guide.email])
    msg.mixed_subtype = 'related'
    msg.attach_alternative(html_content, "text/html")

    logo_path = os.path.join(settings.BASE_DIR, 'static', 'icon.png')
    if os.path.exists(logo_path):
        with open(logo_path, 'rb') as f:
            img = MIMEImage(f.read())
            img.add_header('Content-ID', '<logo_img>')
            img.add_header('Content-Disposition', 'inline', filename='icon.png')
            msg.attach(img)

    msg.send(fail_silently=False)


def send_guide_email_change_confirmation(guide, new_email):
    """
    Sends a confirmation link when the guide updates their email.
    """
    token = secrets.token_urlsafe(48)
    guide.email_change_token = token
    guide.pending_email = new_email
    guide.save(update_fields=['email_change_token', 'pending_email'])

    base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
    confirmation_url = f"{base_url}/guides/verify-email/{token}/"

    subject = _("Confirmez votre nouvelle adresse email - FielMedina")
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@fielmedina.com')
    to_email = [new_email]

    context = {
        'guide_name': guide.user.get_full_name() or guide.user.username,
        'new_email': new_email,
        'confirmation_url': confirmation_url,
        'company_name': 'FielMedina',
    }

    html_content = render_to_string('guides/emails/email_change_confirm.html', context)
    text_content = f"Bonjour,\n\nVeuillez confirmer votre nouvelle adresse email en cliquant sur ce lien: {confirmation_url}"

    msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
    msg.mixed_subtype = 'related'  # Required for CID logo images to show in Gmail
    msg.attach_alternative(html_content, "text/html")

    # Attach logo if exists
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'icon.png')
    if os.path.exists(logo_path):
        with open(logo_path, 'rb') as f:
            img = MIMEImage(f.read())
            img.add_header('Content-ID', '<logo_img>')
            img.add_header('Content-Disposition', 'inline', filename='icon.png')
            msg.attach(img)

    msg.send(fail_silently=False)
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

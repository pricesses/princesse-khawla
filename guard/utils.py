from django.core.mail import send_mail
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.translation import activate

def send_partner_verification_email(partner, request):
    token = default_token_generator.make_token(partner)
    uid = urlsafe_base64_encode(force_bytes(partner.pk))

    lang = getattr(partner, 'language', 'fr')
    activate(lang)

    verification_url = request.build_absolute_uri(
        reverse('guard:verify_partner', kwargs={'uidb64': uid, 'token': token})
    )

    context = {
        'company_name': partner.name,
        'verification_url': verification_url,
        'username': getattr(partner, 'username', ''),
        'password': '',
    }

    subject = "FielMedina - Validation de votre compte"
    text_body = render_to_string('emails/verification.txt', context)
    html_body = render_to_string('emails/verification.html', context)

    send_mail(
        subject,
        text_body,           # ✅ texte fallback
        settings.DEFAULT_FROM_EMAIL,
        [partner.email],
        fail_silently=False,
        html_message=html_body,  # ✅ HTML ajouté !
    )
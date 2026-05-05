from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from .models import GuardUser

@shared_task(bind=True, max_retries=3)
def send_verification_email_task(self, user_id, raw_token):
    try:
        user = GuardUser.objects.get(id=user_id)
        # On essaye de récupérer le nom de l'entreprise si c'est un partenaire
        company_name = getattr(user, 'partner_profile', None)
        company_name = company_name.company_name if company_name else user.email
        
        verification_url = f"{settings.SITE_URL}/verify-email/{raw_token}"
        
        subject = "Vérifiez votre adresse email - FielMedina"
        from_email = settings.DEFAULT_FROM_EMAIL
        to = [user.email]
        
        context = {
            'company_name': company_name,
            'verification_url': verification_url,
        }
        
        text_content = render_to_string('emails/verification.txt', context)
        html_content = render_to_string('emails/verification.html', context)
        
        msg = EmailMultiAlternatives(subject, text_content, from_email, to)
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
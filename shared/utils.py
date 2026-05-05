import os
import logging
from io import BytesIO
from PIL import Image as PilImage
from django.core.files.base import ContentFile
from django.utils.translation import activate, gettext_lazy as _
from django.core import signing
from django.conf import settings

logger = logging.getLogger(__name__)

def optimize_image(image_field, resize_width=None):
    if not image_field:
        return None
    try:
        img = PilImage.open(image_field)
        if img.mode != "RGB":
            img = img.convert("RGB")
        if resize_width and img.width > resize_width:
            ratio = resize_width / float(img.width)
            height = int((float(img.height) * float(ratio)))
            img = img.resize((resize_width, height), PilImage.Resampling.LANCZOS)
        output = BytesIO()
        img.save(output, format="JPEG", quality=80, optimize=True)
        output.seek(0)
        original_name = os.path.basename(image_field.name)
        name_base, _ = os.path.splitext(original_name)
        new_filename = f"{name_base}.jpg"
        return new_filename, ContentFile(output.read())
    except Exception as e:
        logger.error(f"Error optimizing image: {e}")
        return None

def send_validation_email(partner, plain_password=None, lang='fr'):
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from email.mime.image import MIMEImage
 
    activate(lang)
 
    if not partner.email:
        logger.error(f"Impossible d'envoyer l'email : le partenaire {partner.id} n'a pas d'adresse email.")
        return False

    token = signing.dumps({'partner_id': partner.id})
    verify_url = f"{settings.SITE_URL}/partners/verify-email/?token={token}"
 
    context = {
        'company_name': partner.name,
        'verification_url': verify_url,
        'username': partner.user.username if (hasattr(partner, 'user') and partner.user) else (getattr(partner, 'username', None) or partner.name),
        'password': plain_password,
        'site_url': settings.SITE_URL,
    }
    
    subject = _("Validate your FielMedina account — %(partner_name)s") % {'partner_name': partner.name}
    
    try:
        html_content = render_to_string('partners/emails/verification.html', context)
        text_content = render_to_string('partners/emails/verification.txt', context)
    except Exception as e:
        logger.error(f"Erreur rendu template email : {e}")
        return False
 
    email = EmailMultiAlternatives(
        subject,
        text_content,
        settings.DEFAULT_FROM_EMAIL,
        [partner.email],
    )
    email.attach_alternative(html_content, "text/html")
    email.mixed_subtype = 'related'

    # Attach Icon as CID
    try:
        icon_path = os.path.join(settings.BASE_DIR, 'static', 'icon.png')
        if os.path.exists(icon_path):
            with open(icon_path, 'rb') as f:
                icon_data = f.read()
            icon = MIMEImage(icon_data)
            icon.add_header('Content-ID', '<icon_id>')
            icon.add_header('Content-Disposition', 'inline', filename='icon.png')
            email.attach(icon)
        else:
            logger.warning(f"Icône non trouvée pour l'email à {icon_path}")
    except Exception as e:
        logger.error(f"Erreur attachement icône CID : {e}")
 
    try:
        print(f"--- TENTATIVE ENVOI EMAIL A : {partner.email} ---")
        email.send(fail_silently=False)
        logger.info(f"Email de validation envoyé avec succès à {partner.email}")
        return True
    except Exception as e:
        logger.error(f"ÉCHEC ENVOI EMAIL à {partner.email} : {e}")
        print(f"ERREUR ENVOI : {e}")
        return False
from django.contrib.auth.backends import ModelBackend
from partners.models import Partner


class PartnerEmailBackend(ModelBackend):
    """Authentification par email pour les partenaires"""

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = kwargs.get('email', username)
        try:
            partner = Partner.objects.get(email=email)
            if partner.check_password(password):
                return partner
        except Partner.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return Partner.objects.get(pk=user_id)
        except Partner.DoesNotExist:
            return None
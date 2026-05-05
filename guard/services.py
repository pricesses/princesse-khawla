import hashlib
import secrets
from django.utils import timezone
from core.decorators import handle_service_errors
from core.exceptions import DomainException
from .models import EmailVerificationToken

class EmailVerificationService:

    @staticmethod
    @handle_service_errors
    def issue_verification_token(user):
        """
        Génère un token sécurisé, stocke son hash et retourne le token brut.
        """
        # 1. Générer un token aléatoire (48 octets -> env. 64 caractères URL-safe)
        raw_token = secrets.token_urlsafe(48)
        
        # 2. Calculer le hash SHA-256
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        
        # 3. Définir l'expiration (ex: 24 heures)
        expires_at = timezone.now() + timezone.timedelta(hours=24)
        
        # 4. Enregistrer en base
        EmailVerificationToken.objects.create(
            user=user,
            token_hash=token_hash,
            expires_at=expires_at
        )
        
        return raw_token

    @staticmethod
    @handle_service_errors
    def verify_email(raw_token):
        # 1. On transforme le token reçu en hash SHA-256
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        
        # 2. On cherche ce hash en base de données
        try:
            token_obj = EmailVerificationToken.objects.select_related('user').get(
                token_hash=token_hash, 
                is_used=False, 
                expires_at__gt=timezone.now() # Vérifie qu'il n'est pas expiré
            )
        except EmailVerificationToken.DoesNotExist:
            # Ici, le décorateur attrape cette exception et la gère
            raise DomainException("Token invalide ou expiré", code="INVALID_TOKEN")

        # 3. Si on est ici, c'est que le token est bon -> On active l'utilisateur
        user = token_obj.user
        user.is_active = True
        user.save()

        # 4. On "brûle" le token pour qu'il ne soit plus réutilisable (One-time use)
        token_obj.is_used = True
        token_obj.save()
        
        return user

    @staticmethod
    @handle_service_errors
    def resend_verification(email):
        # 1. On cherche l'utilisateur de manière silencieuse
        from .models import User
        user = User.objects.filter(email=email, is_active=False).first()

        # 2. Si l'user n'existe pas ou est déjà actif, on ne lève PAS d'erreur !
        # On fait semblant que tout va bien pour éviter les "enumeration attacks".
        if not user:
            return True 

        # 3. On génère un nouveau token (on réutilise la méthode issue_verification_token)
        # Note: Dans une version pro, on ajouterait un Rate Limit ici (ex: max 1 mail / 2 min)
        raw_token = EmailVerificationService.issue_verification_token(user)

        # 4. Appeler la tâche Celery pour l'envoi (on va la créer juste après)
        from .tasks import send_verification_email_task
        send_verification_email_task.delay(user.id, raw_token)

        return True
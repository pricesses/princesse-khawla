from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class GuardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'guard'

    def ready(self):
        """
        Appelé au démarrage de l'app.
        Importe les signals et enregistre les listeners.
        """
        import guard.signals  # Importe tous les signal handlers
        logger.info("✅ Guard signals registered")
        
        # Importe aussi les signaux du dashboard si activés
        try:
            import guard.dashboard_signals
            logger.info("✅ Dashboard signals registered")
        except ImportError:
            logger.debug("Dashboard signals not yet configured")
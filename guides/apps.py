from django.apps import AppConfig


class GuidesConfig(AppConfig):
    name = "guides"

    def ready(self):
        from . import signals  # noqa: F401 — enregistre les signaux au démarrage
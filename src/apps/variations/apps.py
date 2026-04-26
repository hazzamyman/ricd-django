from django.apps import AppConfig


class VariationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.variations'
    verbose_name = 'Variations'

    def ready(self):
        # Import capture module to register signals
        import apps.variations.capture  # noqa

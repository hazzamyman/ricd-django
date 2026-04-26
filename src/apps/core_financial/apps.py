from django.apps import AppConfig

class CoreFinancialConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core_financial'
    verbose_name = 'Core Financial'

    def ready(self):
        # Import signal handlers
        import apps.core_financial.signals
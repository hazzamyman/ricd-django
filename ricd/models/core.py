from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from decimal import Decimal


class Council(models.Model):
    name = models.CharField(max_length=255)
    abn = models.CharField(max_length=11, blank=True, null=True, validators=[RegexValidator(r'^\d{11}$', 'ABN must be exactly 11 digits')])
    default_suburb = models.CharField(max_length=255, blank=True, null=True)
    default_postcode = models.CharField(max_length=4, blank=True, null=True, validators=[RegexValidator(r'^\d{4}$', 'Postcode must be exactly 4 digits')])
    default_state = models.CharField(max_length=3, default='QLD')
    default_principal_officer = models.ForeignKey('Officer', on_delete=models.SET_NULL, null=True, blank=True, related_name='council_principal_defaults')
    default_senior_officer = models.ForeignKey('Officer', on_delete=models.SET_NULL, null=True, blank=True, related_name='council_senior_defaults')

    # Geographic fields - council-level specifics (don't change per project)
    federal_electorate = models.CharField(max_length=255, blank=True, null=True)
    state_electorate = models.CharField(max_length=255, blank=True, null=True)
    qhigi_region = models.CharField(max_length=255, blank=True, null=True)

    # Housing provider status for requirements determination
    is_registered_housing_provider = models.BooleanField(
        default=False,
        help_text="Whether or not the Council is a Registered Housing Provider. "
                  "This affects whether or not we require leases where council is NOT a registered provider."
    )

    def clean(self):
        """Validate Council fields"""
        if not self.name.strip():
            raise ValidationError({'name': 'Council name is required'})

        # ABN validation - must be 11 digits
        if self.abn:
            if not self.abn.isdigit() or len(self.abn) != 11:
                raise ValidationError({'abn': 'ABN must be exactly 11 digits'})

        # Postcode validation - must be 4 digits for QLD
        if self.default_postcode:
            if not self.default_postcode.isdigit() or len(self.default_postcode) != 4:
                raise ValidationError({'default_postcode': 'Postcode must be exactly 4 digits'})

        # State validation - should be QLD
        if self.default_state and self.default_state != 'QLD':
            raise ValidationError({'default_state': 'Default state must be QLD'})

        # Business rule: if registered housing provider, certain fields might be required
        if self.is_registered_housing_provider:
            # Could add specific validations for registered providers
            pass

    def __str__(self):
        return self.name


class Officer(models.Model):
    """Officer model for dynamic project officers based on users"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='officer_profile')
    position = models.CharField(max_length=255, blank=True, null=True, help_text="Official position title")
    is_active = models.BooleanField(default=True, help_text="Whether this officer is active")
    is_principal = models.BooleanField(default=False, help_text="Can be assigned as Principal Officer")
    is_senior = models.BooleanField(default=False, help_text="Can be assigned as Senior Officer")

    class Meta:
        ordering = ['user__last_name', 'user__first_name']

    def clean(self):
        """Validate Officer fields"""
        if self.is_active and not self.position:
            raise ValidationError({'position': 'Active officers must have a position'})

        # Principal officer validations
        if self.is_principal and not self.is_active:
            raise ValidationError({'is_principal': 'Principal officers must be active'})

        # Senior officer validations
        if self.is_senior and not self.is_active:
            raise ValidationError({'is_senior': 'Senior officers must be active'})

        # Business rule: can't be both principal and senior
        if self.is_principal and self.is_senior:
            raise ValidationError({'is_principal': 'Officer cannot be both principal and senior'})

    def __str__(self):
        full_name = f"{self.user.first_name} {self.user.last_name}".strip()
        if self.position:
            return f"{full_name} ({self.position})"
        return full_name

    @property
    def council_assignment(self):
        """Get officer's council from user profile"""
        if hasattr(self.user, 'profile') and self.user.profile.council:
            return self.user.profile.council
        return None

    @property
    def councils(self):
        """Get list of councils this officer can be assigned to projects in"""
        councils = set()
        if self.council_assignment:
            councils.add(self.council_assignment)
        return councils


class UserProfile(models.Model):
    """User profile to extend Django's base User model"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    council = models.ForeignKey('Council', on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    council_role = models.CharField(
        max_length=20,
        choices=[
            ('manager', 'Manager'),
            ('user', 'User'),
        ],
        null=True,
        blank=True,
        help_text="Role within the council (Manager or User)"
    )

    def __str__(self):
        return f"{self.user.username} - {self.council.name if self.council else 'No Council'}"

    def clean(self):
        """Validate UserProfile fields"""
        if self.council_role and self.council_role not in ['manager', 'user']:
            raise ValidationError({'council_role': 'Council role must be either "manager" or "user"'})

        if self.council and hasattr(self.user, 'officer_profile'):
            officer = self.user.officer_profile
            if officer.council_assignment and officer.council_assignment != self.council:
                raise ValidationError({
                    'council': 'User council must match officer council assignment'
                })

    @property
    def get_council(self):
        return self.council


class Contact(models.Model):
    council = models.ForeignKey('Council', on_delete=models.CASCADE, related_name="contacts")
    name = models.CharField(max_length=255)
    position = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, validators=[RegexValidator(r'^\+?61\s?\d{3}[\s\-]?\d{3}[\s\-]?\d{3}$|^\d{8,10}$', 'Phone number must be a valid Australian phone number (e.g., +61 7 1234 5678 or 0412345678)')])
    address = models.TextField(blank=True, null=True, help_text="Physical address")
    postal_address = models.TextField(blank=True, null=True, help_text="Postal address (optional)")

    def clean(self):
        """Validate Contact fields"""
        if not self.name.strip():
            raise ValidationError({'name': 'Name is required'})

        if not self.position.strip():
            raise ValidationError({'position': 'Position is required'})

        if not self.email.strip():
            raise ValidationError({'email': 'Email is required'})

        # Phone validation - basic check for Australian phone numbers
        import re
        phone_pattern = r'^\+?61\s?\d{3}[\s\-]?\d{3}[\s\-]?\d{3}$|^\d{8,10}$'
        if self.phone and not re.match(phone_pattern, self.phone):
            raise ValidationError({
                'phone': 'Phone number must be a valid Australian phone number (e.g., +61 7 1234 5678 or 0412345678)'
            })

    def __str__(self):
        return f"{self.name} ({self.position})"


class Program(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    budget = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(Decimal('0.01'))])
    funding_source = models.CharField(max_length=50, choices=[
        ("Commonwealth", "Commonwealth"),
        ("State", "State"),
    ], blank=True, null=True)

    def clean(self):
        """Validate Program fields"""
        if not self.name.strip():
            raise ValidationError({'name': 'Program name is required'})

        if self.budget is not None and self.budget <= 0:
            raise ValidationError({'budget': 'Budget must be a positive amount'})

        if self.funding_source and self.funding_source not in ['Commonwealth', 'State']:
            raise ValidationError({'funding_source': 'Funding source must be either "Commonwealth" or "State"'})

    def __str__(self):
        return self.name


class SiteConfiguration(models.Model):
    """Site-wide configuration settings for global formatting and preferences"""

    # Date and time settings
    DATE_FORMAT_CHOICES = [
        ('DD/MM/YYYY', 'DD/MM/YYYY (31/12/2023)'),
        ('MM/DD/YYYY', 'MM/DD/YYYY (12/31/2023)'),
        ('YYYY-MM-DD', 'YYYY-MM-DD (2023-12-31)'),
        ('DD MMM YYYY', 'DD MMM YYYY (31 Dec 2023)'),
        ('MMM DD, YYYY', 'MMM DD, YYYY (Dec 31, 2023)'),
    ]

    TIME_FORMAT_CHOICES = [
        ('12H', '12 Hour (2:30 PM)'),
        ('24H', '24 Hour (14:30)'),
    ]

    TIMEZONE_CHOICES = [
        ('UTC', 'UTC'),
        ('Australia/Sydney', 'Australia/Sydney'),
        ('Australia/Melbourne', 'Australia/Melbourne'),
        ('Australia/Brisbane', 'Australia/Brisbane'),
        ('Australia/Perth', 'Australia/Perth'),
        ('Australia/Adelaide', 'Australia/Adelaide'),
        ('Australia/Darwin', 'Australia/Darwin'),
        ('Australia/Hobart', 'Australia/Hobart'),
        ('US/Eastern', 'US/Eastern'),
        ('US/Central', 'US/Central'),
        ('US/Mountain', 'US/Mountain'),
        ('US/Pacific', 'US/Pacific'),
        ('Europe/London', 'Europe/London'),
        ('Europe/Paris', 'Europe/Paris'),
        ('Asia/Tokyo', 'Asia/Tokyo'),
        ('Asia/Singapore', 'Asia/Singapore'),
    ]

    CURRENCY_CHOICES = [
        ('AUD', 'Australian Dollar (AUD)'),
        ('USD', 'US Dollar (USD)'),
        ('EUR', 'Euro (EUR)'),
        ('GBP', 'British Pound (GBP)'),
        ('JPY', 'Japanese Yen (JPY)'),
        ('CAD', 'Canadian Dollar (CAD)'),
        ('CHF', 'Swiss Franc (CHF)'),
        ('CNY', 'Chinese Yuan (CNY)'),
        ('NZD', 'New Zealand Dollar (NZD)'),
        ('ZAR', 'South African Rand (ZAR)'),
    ]

    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('en-au', 'English (Australia)'),
        ('en-us', 'English (US)'),
        ('en-gb', 'English (UK)'),
    ]

    # Date and time formatting
    date_format = models.CharField(
        max_length=20,
        choices=DATE_FORMAT_CHOICES,
        default='DD/MM/YYYY',
        help_text="Default date format for the entire site"
    )

    time_format = models.CharField(
        max_length=10,
        choices=TIME_FORMAT_CHOICES,
        default='24H',
        help_text="Default time format (12H or 24H)"
    )

    timezone = models.CharField(
        max_length=50,
        choices=TIMEZONE_CHOICES,
        default='Australia/Brisbane',
        help_text="Default timezone for the site"
    )

    # Currency settings
    default_currency = models.CharField(
        max_length=10,
        choices=CURRENCY_CHOICES,
        default='AUD',
        help_text="Default currency for financial displays"
    )

    currency_symbol = models.CharField(
        max_length=5,
        default='$',
        validators=[RegexValidator(r'^.{0,5}$', 'Currency symbol must be 5 characters or less')],
        help_text="Currency symbol to display"
    )

    currency_position = models.CharField(
        max_length=10,
        choices=[
            ('before', 'Before amount ($100)'),
            ('after', 'After amount (100$)'),
        ],
        default='before',
        help_text="Position of currency symbol"
    )

    # Language and localization
    default_language = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default='en-au',
        help_text="Default language for the site"
    )

    # Number formatting
    decimal_places = models.PositiveIntegerField(
        default=2,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="Default number of decimal places for currency"
    )

    thousands_separator = models.CharField(
        max_length=1,
        default=',',
        help_text="Thousands separator character"
    )

    decimal_separator = models.CharField(
        max_length=1,
        default='.',
        help_text="Decimal separator character"
    )

    # Site-wide features
    enable_dark_mode = models.BooleanField(
        default=False,
        help_text="Enable dark mode theme site-wide"
    )

    enable_animations = models.BooleanField(
        default=True,
        help_text="Enable animations and transitions"
    )

    # Maintenance and notifications
    maintenance_mode = models.BooleanField(
        default=False,
        help_text="Enable maintenance mode (shows maintenance page)"
    )

    maintenance_message = models.TextField(
        blank=True,
        null=True,
        help_text="Message to show during maintenance mode"
    )

    # Site branding
    site_title = models.CharField(
        max_length=255,
        default='RICD Portal',
        help_text="Site title displayed in browser and headers"
    )

    site_description = models.TextField(
        blank=True,
        null=True,
        help_text="Site description for SEO and headers"
    )

    # Contact information
    support_email = models.EmailField(
        blank=True,
        null=True,
        help_text="Support email address"
    )

    support_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Support phone number"
    )

    # Metadata
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Configuration"
        verbose_name_plural = "Site Configuration"

    def clean(self):
        """Validate SiteConfiguration fields"""
        if not self.site_title.strip():
            raise ValidationError({'site_title': 'Site title is required'})

        if self.decimal_places < 0 or self.decimal_places > 10:
            raise ValidationError({'decimal_places': 'Decimal places must be between 0 and 10'})

        if len(self.thousands_separator) != 1:
            raise ValidationError({'thousands_separator': 'Thousands separator must be a single character'})

        if len(self.decimal_separator) != 1:
            raise ValidationError({'decimal_separator': 'Decimal separator must be a single character'})

        if self.thousands_separator == self.decimal_separator:
            raise ValidationError({
                'thousands_separator': 'Thousands separator and decimal separator must be different'
            })

        if self.currency_symbol and len(self.currency_symbol) > 5:
            raise ValidationError({'currency_symbol': 'Currency symbol must be 5 characters or less'})

        if self.maintenance_mode and not self.maintenance_message:
            raise ValidationError({
                'maintenance_message': 'Maintenance message is required when maintenance mode is enabled'
            })

        # Email validations
        if self.support_email:
            from django.core.validators import validate_email
            try:
                validate_email(self.support_email)
            except:
                raise ValidationError({'support_email': 'Support email must be a valid email address'})

    def __str__(self):
        return "Site Configuration"

    def save(self, *args, **kwargs):
        # Ensure only one instance exists (singleton pattern)
        if SiteConfiguration.objects.exists() and not self.pk:
            raise ValueError("Only one SiteConfiguration instance can exist")
        super().save(*args, **kwargs)

    @classmethod
    def get_instance(cls):
        """Get the singleton instance of SiteConfiguration"""
        instance, created = cls.objects.get_or_create(pk=1)
        return instance

    def get_currency_display_format(self):
        """Get the currency display format string"""
        if self.currency_position == 'before':
            return f"{self.currency_symbol}{{amount}}"
        else:
            return f"{{amount}}{self.currency_symbol}"

    def format_currency(self, amount):
        """Format a currency amount according to site settings"""
        if amount is None:
            return ""

        try:
            # Format with appropriate separators
            formatted = f"{float(amount):,.{self.decimal_places}f}"
            formatted = formatted.replace(',', self.thousands_separator)
            formatted = formatted.replace('.', self.decimal_separator)

            # Apply currency symbol position
            if self.currency_position == 'before':
                return f"{self.currency_symbol}{formatted}"
            else:
                return f"{formatted}{self.currency_symbol}"
        except (ValueError, TypeError):
            return str(amount)

    def format_date(self, date_obj):
        """Format a date according to site settings"""
        if not date_obj:
            return ""

        try:
            # Import date formatting functions
            from django.utils import formats
            from django.utils import timezone as django_timezone

            # Convert to site timezone if it's a datetime
            if hasattr(date_obj, 'tzinfo') and date_obj.tzinfo is not None:
                site_tz = django_timezone.pytz.timezone(self.timezone)
                date_obj = date_obj.astimezone(site_tz)

            # Use Django's built-in formatting based on our format choice
            format_map = {
                'DD/MM/YYYY': 'd/m/Y',
                'MM/DD/YYYY': 'm/d/Y',
                'YYYY-MM-DD': 'Y-m-d',
                'DD MMM YYYY': 'd M Y',
                'MMM DD, YYYY': 'M d, Y',
            }

            django_format = format_map.get(self.date_format, 'd/m/Y')
            return formats.date_format(date_obj, django_format)
        except Exception:
            return str(date_obj)

    def format_datetime(self, datetime_obj):
        """Format a datetime according to site settings"""
        if not datetime_obj:
            return ""

        try:
            # Import datetime formatting functions
            from django.utils import formats
            from django.utils import timezone as django_timezone

            # Convert to site timezone
            if hasattr(datetime_obj, 'tzinfo') and datetime_obj.tzinfo is not None:
                site_tz = django_timezone.pytz.timezone(self.timezone)
                datetime_obj = datetime_obj.astimezone(site_tz)

            # Use Django's built-in formatting
            format_map = {
                'DD/MM/YYYY': 'd/m/Y',
                'MM/DD/YYYY': 'm/d/Y',
                'YYYY-MM-DD': 'Y-m-d',
                'DD MMM YYYY': 'd M Y',
                'MMM DD, YYYY': 'M d, Y',
            }

            django_format = format_map.get(self.date_format, 'd/m/Y')
            time_format = 'g:i A' if self.time_format == '12H' else 'H:i'

            formatted_date = formats.date_format(datetime_obj, django_format)
            formatted_time = formats.time_format(datetime_obj, time_format)

            return f"{formatted_date} {formatted_time}"
        except Exception:
            return str(datetime_obj)


# Dynamic User Extensions
def user_council_property(self):
    """Dynamic property to get user's council from profile"""
    try:
        return self.profile.council
    except:
        return None

User.council = property(user_council_property)
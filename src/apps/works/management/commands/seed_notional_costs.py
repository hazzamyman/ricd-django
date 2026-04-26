from django.core.management.base import BaseCommand
from django.db import transaction
from apps.works.models import NotionalCostType, NotionalCost, NotionalCostSettings


class Command(BaseCommand):
    help = 'Seed default notional cost types and settings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--financial-year',
            type=str,
            default='2025-26',
            help='Financial year to create costs for (default: 2025-26)'
        )
        parser.add_argument(
            '--inflation-rate',
            type=float,
            default=3.0,
            help='Default inflation rate percentage (default: 3.0)'
        )

    def handle(self, *args, **options):
        financial_year = options['financial_year']
        inflation_rate = options['inflation_rate']
        
        # Create or update settings
        settings, _ = NotionalCostSettings.objects.get_or_create(pk=1)
        settings.default_inflation_rate = inflation_rate
        settings.current_financial_year = financial_year
        settings.save()
        self.stdout.write(f"Settings updated: FY={financial_year}, Inflation={inflation_rate}%")
        
        # Default notional cost types
        cost_types = [
            # Residential - Houses (by bedroom)
            {'name': '1 Bedroom House', 'category': NotionalCostType.Category.RESIDENTIAL, 'cost_basis': NotionalCostType.CostBasis.PER_BEDROOM, 'bedrooms': 1},
            {'name': '2 Bedroom House', 'category': NotionalCostType.Category.RESIDENTIAL, 'cost_basis': NotionalCostType.CostBasis.PER_BEDROOM, 'bedrooms': 2},
            {'name': '3 Bedroom House', 'category': NotionalCostType.Category.RESIDENTIAL, 'cost_basis': NotionalCostType.CostBasis.PER_BEDROOM, 'bedrooms': 3},
            {'name': '4 Bedroom House', 'category': NotionalCostType.Category.RESIDENTIAL, 'cost_basis': NotionalCostType.CostBasis.PER_BEDROOM, 'bedrooms': 4},
            {'name': '5 Bedroom House', 'category': NotionalCostType.Category.RESIDENTIAL, 'cost_basis': NotionalCostType.CostBasis.PER_BEDROOM, 'bedrooms': 5},
            
            # Residential - Duplexes
            {'name': '2 Bedroom Duplex', 'category': NotionalCostType.Category.RESIDENTIAL, 'cost_basis': NotionalCostType.CostBasis.PER_DUPLEX, 'bedrooms': 2},
            {'name': '3 Bedroom Duplex', 'category': NotionalCostType.Category.RESIDENTIAL, 'cost_basis': NotionalCostType.CostBasis.PER_DUPLEX, 'bedrooms': 3},
            
            # Residential - Units
            {'name': '1 Bedroom Unit', 'category': NotionalCostType.Category.RESIDENTIAL, 'cost_basis': NotionalCostType.CostBasis.PER_UNIT, 'bedrooms': 1},
            {'name': '2 Bedroom Unit', 'category': NotionalCostType.Category.RESIDENTIAL, 'cost_basis': NotionalCostType.CostBasis.PER_UNIT, 'bedrooms': 2},
            {'name': '3 Bedroom Unit', 'category': NotionalCostType.Category.RESIDENTIAL, 'cost_basis': NotionalCostType.CostBasis.PER_UNIT, 'bedrooms': 3},
            
            # Residential - Townhouses
            {'name': '1 Bedroom Townhouse', 'category': NotionalCostType.Category.RESIDENTIAL, 'cost_basis': NotionalCostType.CostBasis.PER_BEDROOM, 'bedrooms': 1},
            {'name': '2 Bedroom Townhouse', 'category': NotionalCostType.Category.RESIDENTIAL, 'cost_basis': NotionalCostType.CostBasis.PER_BEDROOM, 'bedrooms': 2},
            {'name': '3 Bedroom Townhouse', 'category': NotionalCostType.Category.RESIDENTIAL, 'cost_basis': NotionalCostType.CostBasis.PER_BEDROOM, 'bedrooms': 3},
            {'name': '4 Bedroom Townhouse', 'category': NotionalCostType.Category.RESIDENTIAL, 'cost_basis': NotionalCostType.CostBasis.PER_BEDROOM, 'bedrooms': 4},
            {'name': '5 Bedroom Townhouse', 'category': NotionalCostType.Category.RESIDENTIAL, 'cost_basis': NotionalCostType.CostBasis.PER_BEDROOM, 'bedrooms': 5},
            
            # Land
            {'name': 'Land Lot', 'category': NotionalCostType.Category.LAND, 'cost_basis': NotionalCostType.CostBasis.PER_LOT, 'bedrooms': None},
            
            # Demolition
            {'name': 'Demolition', 'category': NotionalCostType.Category.DEMOLITION, 'cost_basis': NotionalCostType.CostBasis.PER_LOT, 'bedrooms': None},
            
            # Infrastructure
            {'name': 'Operational Works', 'category': NotionalCostType.Category.INFRASTRUCTURE, 'cost_basis': NotionalCostType.CostBasis.PER_LOT, 'bedrooms': None},
            
            # Planning
            {'name': 'Design Works', 'category': NotionalCostType.Category.PLANNING, 'cost_basis': NotionalCostType.CostBasis.PER_LOT, 'bedrooms': None},
        ]
        
        with transaction.atomic():
            for ct_data in cost_types:
                bedrooms = ct_data.pop('bedrooms')
                ct, created = NotionalCostType.objects.get_or_create(
                    name=ct_data['name'],
                    defaults=ct_data
                )
                
                if created:
                    self.stdout.write(f"Created: {ct.name}")
                else:
                    self.stdout.write(f"Already exists: {ct.name}")
                
                # Create NotionalCost for this financial year with $0
                nc, nc_created = NotionalCost.objects.get_or_create(
                    notional_cost_type=ct,
                    financial_year=financial_year,
                    bedrooms=bedrooms,
                    defaults={'cost_per_unit': 0, 'is_default': True}
                )
                
                if nc_created:
                    self.stdout.write(f"  Created cost for {financial_year}: $0")
        
        self.stdout.write(self.style.SUCCESS(f"Done seeding notional cost types for {financial_year}"))

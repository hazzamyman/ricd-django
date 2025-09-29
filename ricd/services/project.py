from django.utils import timezone
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from loguru import logger
from ..models import Project, Work, FieldVisibilitySetting, ProjectFieldVisibilityOverride


class ProjectService:
    """Service class for project management business logic"""

    @staticmethod
    def calculate_total_funding(project):
        """Calculate total funding from all addresses' budgets"""
        total = sum(address.budget or 0 for address in project.addresses.all())
        logger.info(f"Calculated total funding for project {project.id}: ${total}")
        return total

    @staticmethod
    def calculate_commitments(project):
        """Calculate commitments from funding schedule or estimated amounts"""
        funding_agreement = project.funding_agreement
        if funding_agreement and hasattr(funding_agreement, 'funding_amount'):
            return funding_agreement.funding_amount
        return project.contingency_amount or 0

    @staticmethod
    def calculate_contingency(project):
        """Calculate contingency from commitments and percentage"""
        commitments = project.commitments or ProjectService.calculate_commitments(project)
        if commitments and project.contingency_percentage:
            return (commitments * project.contingency_percentage).quantize(Decimal('0.01'))
        return project.contingency_amount or 0

    @staticmethod
    def check_project_timeliness(project):
        """Check if project is on time, late, or overdue"""
        today = timezone.now().date()

        is_late = False
        is_overdue = False

        if project.state == 'commenced' and project.stage1_target and today > project.stage1_target:
            is_late = True
        if project.state == 'under_construction' and project.stage2_target and today > project.stage2_target:
            is_late = True

        if project.state == 'commenced' and project.stage1_sunset and today > project.stage1_sunset:
            is_overdue = True
        if project.state == 'under_construction' and project.stage2_sunset and today > project.stage2_sunset:
            is_overdue = True

        result = {
            'is_late': is_late,
            'is_overdue': is_overdue,
            'is_on_time': not is_late and not is_overdue,
        }
        logger.info(f"Project {project.id} timeliness check: {result}")
        return result

    @staticmethod
    def get_program_year(project):
        """Auto-calculate program year from funding schedule first release date"""
        if project.funding_schedule and project.funding_schedule.first_release_date:
            return str(project.funding_schedule.first_release_date.year)
        return str(timezone.now().year)

    @staticmethod
    def get_progress_class(progress_percentage):
        """Return CSS class for progress bar color"""
        if progress_percentage >= 75:
            return 'progress-bar-success'
        elif progress_percentage >= 50:
            return 'progress-bar-info'
        elif progress_percentage >= 25:
            return 'progress-bar-warning'
        else:
            return 'progress-bar-danger'

    @staticmethod
    def auto_calculate_stage_dates(project):
        """Auto-calculate stage dates when start_date is set"""
        if not project.start_date:
            return

        updates = {}

        # Calculate stage dates only if they haven't been manually set
        if not project.stage1_target:
            updates['stage1_target'] = project.start_date + relativedelta(months=12)

        if not project.stage1_sunset:
            updates['stage1_sunset'] = project.start_date + relativedelta(months=18)

        if not project.stage2_target:
            if project.stage1_target:
                updates['stage2_target'] = project.stage1_target + relativedelta(months=12)
            else:
                updates['stage2_target'] = project.start_date + relativedelta(months=24)

        if not project.stage2_sunset:
            if project.stage1_sunset:
                updates['stage2_sunset'] = project.stage1_sunset + relativedelta(months=12)
            else:
                updates['stage2_sunset'] = project.start_date + relativedelta(months=30)

        if updates:
            logger.info(f"Auto-calculated stage dates for project {project.id}: {updates}")
        return updates

    @staticmethod
    def get_works_for_project(project):
        """Get all works for a project's addresses"""
        return Work.objects.filter(address__project=project)

    @staticmethod
    def get_field_visibility_settings(council, user=None, project=None):
        """
        Get field visibility settings for a council.
        If project is provided, check for project-specific overrides first.
        If user is provided and is RICD staff, return all fields as visible.
        Otherwise, return the configured settings.
        """
        # RICD users can see all fields
        if user and user.is_authenticated:
            is_ricd = user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists()
            if is_ricd:
                return {choice[0]: True for choice in FieldVisibilitySetting.FIELD_CHOICES}

        # Start with council-level settings
        council_settings = FieldVisibilitySetting.objects.filter(council=council)
        visibility_dict = {choice[0]: True for choice in FieldVisibilitySetting.FIELD_CHOICES}  # Default to visible

        # Override with council configured settings
        for setting in council_settings:
            visibility_dict[setting.field_name] = setting.visible_to_council_users

        # If project is provided, override with project-specific settings
        if project:
            project_overrides = ProjectFieldVisibilityOverride.objects.filter(project=project)
            for override in project_overrides:
                visibility_dict[override.field_name] = override.visible_to_council_users

        return visibility_dict

    @staticmethod
    def is_field_visible(field_name, council, user=None, project=None):
        """
        Check if a specific field should be visible to a user for a council.
        If project is provided, check for project-specific overrides.
        """
        settings = ProjectService.get_field_visibility_settings(council, user, project)
        return settings.get(field_name, True)  # Default to visible if not configured
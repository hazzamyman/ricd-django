"""
Consolidated models layer — imports all domain models from local files.
Copied from individual apps during Phase 1A refactoring.
"""

# Council & Program models
from .councils_models import Council, CouncilContact
from .programs_models import Program, ProgramBudget

# Project models
from .projects_models import Project, Comment

# Land Infrastructure models
from .land_infra_models import LandProject, LandTenure, DevelopmentApplication

# Funding & Payment models
from .funding_models import (
    PaymentRule,
    FundingAgreement,
    BriefFinancialApproval,
    FundingNotice,
    ExpenseClaim,
    Delegation,
    FundingApproval,
    FundingSchedule,
    ProjectStateLog,
    WorkFunding,
    Approval,
    WorkflowAction,
    AuditLog,
)
from .payments_models import Payment

# Variation & Stage models
from .variations_models import VariationType, Variation, VariationFundingSchedule, VariationContactDetails, VariationDateChange
from .stages_models import Stage, WorkStep

# Report models
from .reports_models import (
    MonthlyTrackerItemGroup,
    MonthlyTrackerItem,
    MonthlyTracker,
    MonthlyTrackerEntry,
    QuarterlyReportItemGroup,
    QuarterlyReportItem,
    QuarterlyReport,
    QuarterlyReportEntry,
    QuarterlyReportAttachment,
    StageReport,
    StageReportItem,
    StageReportAttachment,
)

# Contractor & Address models
from .contractors_models import Contractor
from .addresses_models import Suburb, Address

# Account & User models
from .accounts_models import Profile, GroupPermission

# Contract & Document models
from .contracts_models import Contract, ContractMeeting
from .documents_models import DocumentType, ProjectDocument

# Defect & Work models
from .defects_models import Defect
from .works_models import WorkType, NotionalCost, NotionalCostSettings, Work, WorkStepTemplate

__all__ = [
    # Council & Program
    'Council', 'CouncilContact', 'Program', 'ProgramBudget',
    # Project
    'Project', 'Comment',
    # Land Infrastructure
    'LandProject', 'LandTenure', 'DevelopmentApplication',
    # Funding & Payment
    'PaymentRule', 'FundingAgreement', 'BriefFinancialApproval',
    'FundingNotice', 'ExpenseClaim', 'Delegation', 'FundingApproval',
    'FundingSchedule', 'ProjectStateLog', 'WorkFunding',
    'Approval', 'WorkflowAction', 'AuditLog', 'Payment',
    # Variation & Stage
    'VariationType', 'Variation', 'VariationFundingSchedule',
    'VariationContactDetails', 'VariationDateChange',
    'Stage', 'WorkStep',
    # Report
    'MonthlyTrackerItemGroup', 'MonthlyTrackerItem', 'MonthlyTracker',
    'MonthlyTrackerEntry', 'QuarterlyReportItemGroup', 'QuarterlyReportItem',
    'QuarterlyReport', 'QuarterlyReportEntry', 'QuarterlyReportAttachment',
    'StageReport', 'StageReportItem', 'StageReportAttachment',
    # Contractor & Address
    'Contractor', 'Suburb', 'Address',
    # Account
    'Profile', 'GroupPermission',
    # Contract & Document
    'Contract', 'ContractMeeting', 'DocumentType', 'ProjectDocument',
    # Defect & Work
    'Defect', 'WorkType', 'NotionalCost', 'NotionalCostSettings', 'Work', 'WorkStepTemplate',
]

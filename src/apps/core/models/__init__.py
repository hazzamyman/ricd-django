"""
Consolidated models layer — imports all domain models from local files.
Copied from individual apps during Phase 1A refactoring.
"""

# Council & Program models
from .councils_models import Council, CouncilContact
from .programs_models import Program, ProgramBudget

# Project models
from .projects_models import Project

# Comment system
from .comments_models import Comment, CommentSettings, Notice, NoticeTarget

# Land Infrastructure models
from .land_infra_models import LandTenure, DevelopmentApplication, LandPreCondition

# Funding & Payment models
from .funding_models import (
    PaymentRule,
    PaymentRuleMilestone,
    FundingAgreement,
    BriefFinancialApproval,
    BriefFinancialApprovalItem,
    PaymentAllocation,
    FundingNotice,
    ExpenseClaim,
    ExpenseClaimAttachment,
    Delegation,
    FundingSchedule,
    ProjectStateLog,
    WorkFunding,
    Approval,
    WorkflowAction,
    AuditLog,
    ForwardRPFAgreement,
    InterimFRPAgreement,
)
from .payments_models import Payment, PaymentMilestoneSchedule, PaymentMilestoneRule

# Variation & Stage models
from .variations_models import (
    VariationType, Variation, VariationItem, VariationFundingSchedule,
    VariationContactDetails, VariationDateChange,
)
from .stages_models import Stage, WorkStep

# Report models
from .reports_models import (
    CouncilTrackerConfig,
    MonthlyTracker,
    MonthlyTrackerWorkEntry,
    QuarterlyReportItemGroup,
    QuarterlyReportItem,
    QuarterlyReport,
    QuarterlyReportEntry,
    QuarterlyReportExpenditureItem,
    QuarterlyReportAttachment,
    StageReport,
    StageReportItem,
    StageReportAttachment,
)

# Contractor & Address models
from .contractors_models import Contractor
from .addresses_models import (
    Suburb, Address, StateElectorate, FederalElectorate, QhigiRegion,
)

# Account & User models
from .accounts_models import Profile, GroupPermission, SiteSettings

# Contract & Document models
from .contracts_models import Contract, ContractMeeting
from .documents_models import DocumentType, ProjectDocument

# Defect & Work models
from .defects_models import Defect
from .works_models import (
    WorkType, NotionalCost, NotionalCostSettings, Work,
    WorkStepDefinition, WorkStepGroup, WorkStepGroupItem, ConstructionMethod,
    StageItemDefinition, StageItemGroup, StageItemGroupItem,
)

__all__ = [
    # Council & Program
    'Council', 'CouncilContact', 'Program', 'ProgramBudget',
    # Project
    'Project',
    # Comment system
    'Comment', 'CommentSettings', 'Notice', 'NoticeTarget',
    # Land Infrastructure
    'LandTenure', 'DevelopmentApplication', 'LandPreCondition',
    # Funding & Payment
    'PaymentRule', 'PaymentRuleMilestone', 'FundingAgreement', 'BriefFinancialApproval', 'BriefFinancialApprovalItem', 'PaymentAllocation',
    'FundingNotice', 'ExpenseClaim', 'ExpenseClaimAttachment', 'Delegation',
    'FundingSchedule', 'ProjectStateLog', 'WorkFunding',
    'Approval', 'WorkflowAction', 'AuditLog', 'Payment',
    'PaymentMilestoneSchedule', 'PaymentMilestoneRule',
    'ForwardRPFAgreement', 'InterimFRPAgreement',
    # Variation & Stage
    'VariationType', 'Variation', 'VariationItem', 'VariationFundingSchedule',
    'VariationContactDetails', 'VariationDateChange',
    'Stage', 'WorkStep',
    # Report
    'CouncilTrackerConfig', 'MonthlyTracker', 'MonthlyTrackerWorkEntry', 'QuarterlyReportItemGroup', 'QuarterlyReportItem',
    'QuarterlyReport', 'QuarterlyReportEntry', 'QuarterlyReportExpenditureItem', 'QuarterlyReportAttachment',
    'StageReport', 'StageReportItem', 'StageReportAttachment',
    # Contractor & Address
    'Contractor', 'Suburb', 'Address',
    'StateElectorate', 'FederalElectorate', 'QhigiRegion',
    # Account
    'Profile', 'GroupPermission', 'SiteSettings',
    # Contract & Document
    'Contract', 'ContractMeeting', 'DocumentType', 'ProjectDocument',
    # Defect & Work
    'Defect', 'WorkType', 'NotionalCost', 'NotionalCostSettings', 'Work',
    'WorkStepDefinition', 'WorkStepGroup', 'WorkStepGroupItem', 'ConstructionMethod',
    'StageItemDefinition', 'StageItemGroup', 'StageItemGroupItem',
]

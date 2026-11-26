"""Modelos ORM da aplicação."""

from app.models.ai import (
    AiConversation,
    AiMessage,
    ConversationStatus,
    MessageDirection,
)
from app.models.appointment import Appointment, AppointmentStatus
from app.models.audit import AuditLog
from app.models.client import Client, ClientScoreEvent, ClientScoreRating, LgpdConsent
from app.models.finance import (
    AccountType,
    FinancialAccount,
    FinancialCategory,
    FinancialEntry,
    FinancialEntryStatus,
    FinancialEntryType,
)
from app.models.medical_record import MedicalRecord, MedicalRecordAttachment
from app.models.package import Package, PackageItem
from app.models.payment import PaymentIntent, PaymentStatus
from app.models.service import Service
from app.models.subscription import (
    ClientSubscription,
    ClientSubscriptionStatus,
    SubscriptionUsage,
)
from app.models.subscription_plan import (
    BillingCycle,
    SubscriptionPlan,
    SubscriptionPlanItem,
)
from app.models.tenant import TaxRegime, Tenant, TenantSettings
from app.models.user import CommissionBase, User, UserRole

__all__ = [
    "AccountType",
    "AiConversation",
    "AiMessage",
    "Appointment",
    "AppointmentStatus",
    "AuditLog",
    "BillingCycle",
    "Client",
    "ClientScoreEvent",
    "ClientScoreRating",
    "ClientSubscription",
    "ClientSubscriptionStatus",
    "CommissionBase",
    "ConversationStatus",
    "FinancialAccount",
    "FinancialCategory",
    "FinancialEntry",
    "FinancialEntryStatus",
    "FinancialEntryType",
    "LgpdConsent",
    "MedicalRecord",
    "MedicalRecordAttachment",
    "MessageDirection",
    "Package",
    "PackageItem",
    "PaymentIntent",
    "PaymentStatus",
    "Service",
    "SubscriptionPlan",
    "SubscriptionPlanItem",
    "SubscriptionUsage",
    "TaxRegime",
    "Tenant",
    "TenantSettings",
    "User",
    "UserRole",
]

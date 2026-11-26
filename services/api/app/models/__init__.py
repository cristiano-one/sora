"""Modelos ORM da aplicação."""

from app.models.ai import (
    AiConversation,
    AiMessage,
    ConversationStatus,
    MessageDirection,
)
from app.models.appointment import Appointment, AppointmentStatus
from app.models.audit import AuditLog
from app.models.automation import (
    AutomationRule,
    AutomationRun,
    AutomationRunStatus,
    AutomationTrigger,
)
from app.models.client import Client, ClientScoreEvent, ClientScoreRating, LgpdConsent
from app.models.client_credit import ClientCredit, ClientCreditUsage
from app.models.finance import (
    AccountType,
    FinancialAccount,
    FinancialCategory,
    FinancialEntry,
    FinancialEntryStatus,
    FinancialEntryType,
)
from app.models.fiscal import FiscalInvoice, FiscalInvoiceStatus
from app.models.inventory import InventoryItem, StockMovement, StockMovementType
from app.models.medical_record import MedicalRecord, MedicalRecordAttachment
from app.models.package import Package, PackageItem
from app.models.payment import PaymentIntent, PaymentStatus
from app.models.payroll import PayrollEntry, PayrollKind
from app.models.sale import (
    Sale,
    SaleItem,
    SaleItemCategory,
    SalePaymentMethod,
    SaleStatus,
)
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
from app.models.tenant import (
    BusinessProfile,
    TaxRegime,
    Tenant,
    TenantSettings,
    supports_medical_records,
)
from app.models.tithe import TitheDelivery
from app.models.user import CommissionBase, EmploymentType, User, UserRole
from app.models.whatsapp import (
    TenantWhatsAppAccount,
    WhatsAppConnectionStatus,
    WhatsAppRegistrationStatus,
)

__all__ = [
    "AccountType",
    "AiConversation",
    "AiMessage",
    "Appointment",
    "AppointmentStatus",
    "AuditLog",
    "AutomationRule",
    "AutomationRun",
    "AutomationRunStatus",
    "AutomationTrigger",
    "BillingCycle",
    "BusinessProfile",
    "Client",
    "ClientCredit",
    "ClientCreditUsage",
    "ClientScoreEvent",
    "ClientScoreRating",
    "ClientSubscription",
    "ClientSubscriptionStatus",
    "CommissionBase",
    "ConversationStatus",
    "EmploymentType",
    "FinancialAccount",
    "FinancialCategory",
    "FinancialEntry",
    "FinancialEntryStatus",
    "FinancialEntryType",
    "FiscalInvoice",
    "FiscalInvoiceStatus",
    "InventoryItem",
    "LgpdConsent",
    "MedicalRecord",
    "MedicalRecordAttachment",
    "MessageDirection",
    "Package",
    "PackageItem",
    "PaymentIntent",
    "PaymentStatus",
    "PayrollEntry",
    "PayrollKind",
    "Sale",
    "SaleItem",
    "SaleItemCategory",
    "SalePaymentMethod",
    "SaleStatus",
    "Service",
    "StockMovement",
    "StockMovementType",
    "SubscriptionPlan",
    "SubscriptionPlanItem",
    "SubscriptionUsage",
    "TaxRegime",
    "Tenant",
    "TenantSettings",
    "TenantWhatsAppAccount",
    "TitheDelivery",
    "User",
    "UserRole",
    "WhatsAppConnectionStatus",
    "WhatsAppRegistrationStatus",
    "supports_medical_records",
]

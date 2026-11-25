"""Modelos ORM da aplicação."""

from app.models.appointment import Appointment, AppointmentStatus
from app.models.audit import AuditLog
from app.models.client import Client, ClientScoreEvent, ClientScoreRating, LgpdConsent
from app.models.medical_record import MedicalRecord, MedicalRecordAttachment
from app.models.package import Package, PackageItem
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
from app.models.tenant import TaxRegime, Tenant
from app.models.user import CommissionBase, User, UserRole

__all__ = [
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
    "LgpdConsent",
    "MedicalRecord",
    "MedicalRecordAttachment",
    "Package",
    "PackageItem",
    "Service",
    "SubscriptionPlan",
    "SubscriptionPlanItem",
    "SubscriptionUsage",
    "TaxRegime",
    "Tenant",
    "User",
    "UserRole",
]

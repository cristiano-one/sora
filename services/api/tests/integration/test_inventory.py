"""Estoque de insumos: CRUD, movimentos e isolamento multi-tenant."""

from uuid import uuid4

import pytest
from app.models import UserRole

pytestmark = [pytest.mark.security, pytest.mark.integration]

INVENTORY = "/api/v1/inventory"
LOGIN = "/api/v1/auth/login"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _login(auth_client, user) -> str:
    response = await auth_client.post(
        LOGIN,
        json={
            "tenant_slug": user.tenant_slug,
            "email": user.email,
            "password": user.password,
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


async def _create_item(auth_client, token: str, suffix: str) -> dict:
    response = await auth_client.post(
        INVENTORY,
        headers=_auth(token),
        json={
            "name": f"Insumo {suffix}",
            "unit": "ml",
            "quantity": "5.000",
            "min_quantity": "2.000",
            "unit_cost": "3.50",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_owner_manages_inventory_and_movements(
    auth_client,
    tenant_users,
) -> None:
    token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    item = await _create_item(auth_client, token, uuid4().hex[:6])
    assert item["quantity"] == "5.000"
    assert item["low_stock"] is False
    assert item["total_value"] == "17.50"

    entry = await auth_client.post(
        f"{INVENTORY}/{item['id']}/movements",
        headers=_auth(token),
        json={
            "kind": "IN",
            "quantity": "10.000",
            "reason": "Compra",
            "document_type": "NFE",
            "document_number": "12345",
            "document_series": "1",
            "supplier_name": "Fornecedor Demo",
            "supplier_tax_id": "12.345.678/0001-90",
            "issue_date": "2027-02-10",
            "total_amount": "35.00",
            "payment_method": "PIX",
            "access_key": "1" * 44,
        },
    )
    assert entry.status_code == 201, entry.text
    entry_body = entry.json()
    assert entry_body["document_type"] == "NFE"
    assert entry_body["document_number"] == "12345"
    assert entry_body["document_series"] == "1"
    assert entry_body["supplier_name"] == "Fornecedor Demo"
    assert entry_body["supplier_tax_id"] == "12.345.678/0001-90"
    assert entry_body["issue_date"] == "2027-02-10"
    assert entry_body["total_amount"] == "35.00"
    assert entry_body["payment_method"] == "PIX"
    assert entry_body["access_key"] == "1" * 44

    output = await auth_client.post(
        f"{INVENTORY}/{item['id']}/movements",
        headers=_auth(token),
        json={"kind": "OUT", "quantity": "13.000", "reason": "Uso"},
    )
    assert output.status_code == 201

    items = await auth_client.get(INVENTORY, headers=_auth(token))
    updated = next(row for row in items.json() if row["id"] == item["id"])
    assert updated["quantity"] == "2.000"
    assert updated["low_stock"] is True

    adjusted = await auth_client.post(
        f"{INVENTORY}/{item['id']}/movements",
        headers=_auth(token),
        json={"kind": "ADJUSTMENT", "quantity": "8.000", "reason": "Contagem"},
    )
    assert adjusted.status_code == 201

    movements = await auth_client.get(
        f"{INVENTORY}/{item['id']}/movements",
        headers=_auth(token),
    )
    assert movements.status_code == 200
    assert len(movements.json()) == 3
    assert movements.json()[0]["kind"] == "ADJUSTMENT"
    entry_saved = next(row for row in movements.json() if row["kind"] == "IN")
    assert entry_saved["document_number"] == "12345"
    assert entry_saved["supplier_name"] == "Fornecedor Demo"
    assert entry_saved["total_amount"] == "35.00"

    renamed = await auth_client.patch(
        f"{INVENTORY}/{item['id']}",
        headers=_auth(token),
        json={"name": f"Renomeado {uuid4().hex[:4]}"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"].startswith("Renomeado")


async def test_inventory_document_fields_only_for_entries(
    auth_client,
    tenant_users,
) -> None:
    token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    item = await _create_item(auth_client, token, uuid4().hex[:6])

    output_with_document = await auth_client.post(
        f"{INVENTORY}/{item['id']}/movements",
        headers=_auth(token),
        json={
            "kind": "OUT",
            "quantity": "1.000",
            "document_type": "RECEIPT",
            "document_number": "999",
        },
    )
    assert output_with_document.status_code == 422

    invalid_access_key = await auth_client.post(
        f"{INVENTORY}/{item['id']}/movements",
        headers=_auth(token),
        json={
            "kind": "IN",
            "quantity": "1.000",
            "document_type": "NFE",
            "access_key": "123",
        },
    )
    assert invalid_access_key.status_code == 422

    negative_total = await auth_client.post(
        f"{INVENTORY}/{item['id']}/movements",
        headers=_auth(token),
        json={
            "kind": "IN",
            "quantity": "1.000",
            "document_type": "RECEIPT",
            "total_amount": "-1.00",
        },
    )
    assert negative_total.status_code == 422


async def test_inventory_rejects_negative_balance_and_duplicate_name(
    auth_client,
    tenant_users,
) -> None:
    token = await _login(auth_client, tenant_users.users[UserRole.OWNER])
    suffix = uuid4().hex[:6]
    item = await _create_item(auth_client, token, suffix)

    too_much = await auth_client.post(
        f"{INVENTORY}/{item['id']}/movements",
        headers=_auth(token),
        json={"kind": "OUT", "quantity": "99.000"},
    )
    assert too_much.status_code == 422

    duplicate = await auth_client.post(
        INVENTORY,
        headers=_auth(token),
        json={"name": item["name"], "unit": "ml"},
    )
    assert duplicate.status_code == 409


async def test_inventory_is_manager_only_and_cross_tenant_hidden(
    auth_client,
    tenant_users,
    auth_user,
) -> None:
    owner_token = await _login(
        auth_client,
        tenant_users.users[UserRole.OWNER],
    )
    item = await _create_item(auth_client, owner_token, uuid4().hex[:6])

    collaborator_token = await _login(
        auth_client,
        tenant_users.users[UserRole.COLLABORATOR],
    )
    forbidden = await auth_client.get(
        INVENTORY,
        headers=_auth(collaborator_token),
    )
    assert forbidden.status_code == 403

    other_token = await _login(auth_client, auth_user)
    other_list = await auth_client.get(INVENTORY, headers=_auth(other_token))
    assert other_list.status_code == 200
    assert all(row["id"] != item["id"] for row in other_list.json())

    cross = await auth_client.patch(
        f"{INVENTORY}/{item['id']}",
        headers=_auth(other_token),
        json={"name": "Invasão"},
    )
    assert cross.status_code == 404

    deleted = await auth_client.delete(
        f"{INVENTORY}/{item['id']}",
        headers=_auth(owner_token),
    )
    assert deleted.status_code == 204

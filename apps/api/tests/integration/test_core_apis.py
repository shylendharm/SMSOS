import uuid
import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.seed.demo_data import seed_demo_data


@pytest.mark.asyncio
async def test_all_core_apis_integration(test_engine):
    await seed_demo_data()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Login to get token
        login_res = await ac.post("/api/v1/auth/login", json={"email": "owner@smsos.in", "password": "admin123"})
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Health check (public)
        health_res = await ac.get("/api/v1/health")
        assert health_res.status_code == 200
        assert health_res.json()["status"] == "ok"

        # 3. Order CRUD integration
        order_res = await ac.post(
            "/api/v1/orders",
            headers=headers,
            json={
                "customer_phone": f"+91987{uuid.uuid4().hex[:7]}",
                "customer_name": "Test Client",
                "items": [{"item_name": "Chocolate Cake", "quantity": 1, "unit_price": 350.0}],
                "notes": "Urgent delivery",
            },
        )
        assert order_res.status_code == 200
        created_order = order_res.json()
        order_id = created_order["id"]
        assert created_order["status"] == "pending"

        # Get single order
        get_order_res = await ac.get(f"/api/v1/orders/{order_id}", headers=headers)
        assert get_order_res.status_code == 200
        assert get_order_res.json()["id"] == order_id

        # Update order status
        update_order_res = await ac.put(f"/api/v1/orders/{order_id}", headers=headers, json={"status": "ready"})
        assert update_order_res.status_code == 200
        assert update_order_res.json()["status"] == "ready"

        # 4. Reservation CRUD + conflict detection
        res_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        table_name = f"Table_{uuid.uuid4().hex[:4]}"
        res_create = await ac.post(
            "/api/v1/reservations",
            headers=headers,
            json={
                "customer_name": "Jane Doe",
                "customer_phone": f"+91987{uuid.uuid4().hex[:7]}",
                "reserved_at": res_time,
                "party_size": 4,
                "table_or_slot": table_name,
            },
        )
        assert res_create.status_code == 200
        res_id = res_create.json()["id"]

        # Conflict detection: same table and time
        res_conflict = await ac.post(
            "/api/v1/reservations",
            headers=headers,
            json={
                "customer_name": "Mark Smith",
                "reserved_at": res_time,
                "party_size": 2,
                "table_or_slot": table_name,
            },
        )
        assert res_conflict.status_code == 409
        assert res_conflict.json()["error"]["code"] == "CONFLICT"

        # Patch reservation
        patch_res = await ac.patch(f"/api/v1/reservations/{res_id}", headers=headers, json={"status": "completed"})
        assert patch_res.status_code == 200
        assert patch_res.json()["status"] == "completed"

        # 5. Inventory CRUD + low stock query
        inv_item_name = f"Milk_{uuid.uuid4().hex[:4]}"
        inv_create = await ac.post(
            "/api/v1/inventory",
            headers=headers,
            json={
                "item_name": inv_item_name,
                "current_quantity": 2.0,
                "unit": "liters",
                "low_threshold": 5.0,
            },
        )
        assert inv_create.status_code == 200
        inv_data = inv_create.json()
        assert inv_data["is_low_stock"] is True

        # Query low stock items only
        inv_low = await ac.get("/api/v1/inventory?low_stock_only=true", headers=headers)
        assert inv_low.status_code == 200
        low_items = inv_low.json()
        assert any(item["item_name"] == inv_item_name for item in low_items)

        # Patch inventory stock
        inv_id = inv_data["id"]
        inv_patch = await ac.patch(f"/api/v1/inventory/{inv_id}", headers=headers, json={"quantity_change": 10.0})
        assert inv_patch.status_code == 200
        assert float(inv_patch.json()["current_quantity"]) == 12.0
        assert inv_patch.json()["is_low_stock"] is False

        # 6. Catalog GET & POST
        cat_create = await ac.post(
            "/api/v1/catalog",
            headers=headers,
            json={"name": f"Cold Coffee {uuid.uuid4().hex[:4]}", "price": 100.0, "unit": "cup", "category": "Beverages"},
        )
        assert cat_create.status_code == 200

        cat_list = await ac.get("/api/v1/catalog", headers=headers)
        assert cat_list.status_code == 200
        assert len(cat_list.json()) >= 1

        # 7. Customers GET & POST
        cust_list = await ac.get("/api/v1/customers", headers=headers)
        assert cust_list.status_code == 200
        assert len(cust_list.json()) >= 1

        # 8. Analytics summary
        analytics_res = await ac.get("/api/v1/analytics/summary", headers=headers)
        assert analytics_res.status_code == 200
        assert "total_orders" in analytics_res.json()

        # 9. Conversations endpoint
        conv_res = await ac.get("/api/v1/conversations", headers=headers)
        assert conv_res.status_code == 200
        assert isinstance(conv_res.json(), list)

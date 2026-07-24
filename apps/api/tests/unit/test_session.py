import uuid
import pytest
from sqlalchemy import select
from app.db.session import get_db_session
from app.db.models.business import Business


@pytest.mark.asyncio
async def test_db_session_lifecycle():
    phone = f"+1555{uuid.uuid4().hex[:7]}"
    async for session in get_db_session():
        biz = Business(
            name="Session Lifecycle Test",
            business_type="bakery",
            phone_number=phone,
            timezone="UTC",
        )
        session.add(biz)
        await session.flush()
        assert biz.id is not None


@pytest.mark.asyncio
async def test_db_session_rollback_on_error():
    name = f"Rollback Test {uuid.uuid4().hex[:6]}"
    phone = f"+1555{uuid.uuid4().hex[:7]}"
    try:
        async for session in get_db_session():
            biz = Business(
                name=name,
                business_type="bakery",
                phone_number=phone,
            )
            session.add(biz)
            await session.flush()
            raise ValueError("Forced error to test rollback")
    except ValueError:
        pass

    # Verify that the business was NOT committed
    async for session in get_db_session():
        res = await session.execute(select(Business).where(Business.name == name))
        assert res.scalars().first() is None

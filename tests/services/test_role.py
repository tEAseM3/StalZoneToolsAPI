from app.models.role import Role
from app.services.role import get_role_by_name


async def test_get_role_by_name_returns_existing_role(db_session):
    role = Role(name="admin")
    db_session.add(role)
    await db_session.commit()

    found_role = await get_role_by_name(db_session, "admin")

    assert found_role is not None
    assert found_role.id == role.id


async def test_get_role_by_name_returns_none_when_role_is_missing(db_session):
    role = await get_role_by_name(db_session, "unknown")

    assert role is None

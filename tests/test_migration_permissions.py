from pathlib import Path


def test_permission_seed_migration_assigns_explicit_permissions_to_both_roles():
    migration = Path("alembic/versions/9f1c7a4b2d8e_seed_resource_action_permissions.py").read_text(
        encoding="utf-8"
    )

    assert '"profile:read"' in migration
    assert '"items:read"' in migration
    assert '"hideout:read"' in migration
    assert '"auction:read"' in migration
    assert '"system:read"' in migration
    user_assignment = '_assign_permissions(role_permissions, roles, permissions, "user", '
    admin_assignment = '_assign_permissions(role_permissions, roles, permissions, "admin", '
    assert user_assignment in migration
    assert admin_assignment in migration

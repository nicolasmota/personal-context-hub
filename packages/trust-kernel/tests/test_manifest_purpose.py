from pch_core.errors import ValidationFailed


def test_unscoped_manifest_fails(hub):
    link = hub.mint_link()
    paired = hub.pair(link["code"])
    actor = paired["connection_id"]
    hub.create_grant(actor, "read_active_projects", None, None)
    try:
        hub.create_manifest(actor, "", ["project.read"], {})
        raise AssertionError("expected validation")
    except ValidationFailed:
        pass

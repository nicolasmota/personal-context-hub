from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from pch_core.schema.contract import OmissionNote, envelope_json_schema
from pch_core.service import OWNER
from pch_core.testing.incident_offer_seed import seed_incident_offer
from pydantic import ValidationError as PydanticValidationError

REPO = Path(__file__).resolve().parents[3]
SCHEMA_PATH = REPO / "docs" / "reference" / "context-contract.schema.json"


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _validator():
    schema = _load_schema()
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _base_package() -> dict:
    return {
        "contract_id": "contract_test",
        "purpose": "continue the incident",
        "situation": None,
        "candidates": [],
        "goals": [],
        "preferences": [],
        "memories": [],
        "decisions": [],
        "constraints": [],
        "state": [],
        "relations": [],
        "references": [],
        "conflicts": [],
        "granted_scope": {
            "grant_id": "owner",
            "selectors": {},
            "classification_ceiling": "sensitive",
            "capabilities": ["*"],
            "summary_human": "owner",
        },
        "omissions": [],
        "capture_hints": [],
        "assembled_at": "2026-09-15T00:00:00Z",
        "sufficient": False,
    }


def _pair(hub, name: str):
    link = hub.mint_link(name)
    return hub.pair(link["code"])


def test_published_schema_matches_generator():
    committed = _load_schema()
    assert committed == envelope_json_schema()


def test_well_formed_sample_passes_without_hub():
    _validator().validate(_base_package())


def test_package_missing_sufficient_fails_published_envelope():
    package = _base_package()
    del package["sufficient"]
    with pytest.raises(ValidationError):
        _validator().validate(package)


def test_package_missing_omissions_fails_published_envelope():
    package = _base_package()
    del package["omissions"]
    with pytest.raises(ValidationError):
        _validator().validate(package)


def test_scope_missing_summary_human_fails_published_envelope():
    package = _base_package()
    del package["granted_scope"]["summary_human"]
    with pytest.raises(ValidationError):
        _validator().validate(package)


def test_leaking_omission_fails_published_envelope():
    package = _base_package()
    package["omissions"] = [
        {
            "category": "not_relevant",
            "label": "off-task context withheld",
            "count": 1,
            "id": "mem_01HIDDEN",
        }
    ]
    with pytest.raises(ValidationError):
        _validator().validate(package)


@pytest.mark.parametrize("extra", [{"title": "Rye bread"}, {"body": "I prefer rye"}])
def test_omission_title_or_body_fails_published_envelope(extra: dict):
    note = {
        "category": "not_relevant",
        "label": "off-task context withheld",
        "count": 1,
        **extra,
    }
    package = _base_package()
    package["omissions"] = [note]
    with pytest.raises(ValidationError):
        _validator().validate(package)


def test_closed_omission_is_accepted():
    package = _base_package()
    package["omissions"] = [
        {
            "category": "not_relevant",
            "label": "off-task context withheld",
            "count": 10,
        }
    ]
    package["sufficient"] = True
    _validator().validate(package)


def test_omission_note_model_rejects_extra_keys():
    with pytest.raises(PydanticValidationError):
        OmissionNote(
            category="not_relevant",
            label="off-task context withheld",
            count=1,
            id="mem_01HIDDEN",
        )


def test_hub_incident_package_fits_published_envelope(hub):
    seed_incident_offer(hub)
    package = hub.get_context_contract(OWNER, "continue the incident")
    _validator().validate(package)
    assert package["purpose"] == "continue the incident"
    assert package["granted_scope"]["summary_human"]
    assert "omissions" in package
    assert isinstance(package["sufficient"], bool)


def test_work_scoped_incident_omissions_fit_envelope(hub):
    seed = seed_incident_offer(hub)
    worker = _pair(hub, "work-agent")
    hub.create_grant(
        worker["connection_id"],
        None,
        ["project.read", "commitment.read", "memory.retrieve", "profile.read"],
        {"project": seed["incident"]["id"]},
        "private",
    )
    package = hub.get_context_contract(worker["connection_id"], "continue the incident")
    _validator().validate(package)
    blob = json.dumps(package["omissions"])
    assert "Northwind" not in blob
    assert seed["offer"]["id"] not in blob
    assert "4242" not in json.dumps(package)
    assert all(set(note) <= {"category", "label", "count"} for note in package["omissions"])
    stored = hub.get(seed["offer"]["id"])
    assert stored["title"] == "Northwind offer"

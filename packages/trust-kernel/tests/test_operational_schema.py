import pytest
from pch_core.schema.contract import SituationRef
from pch_core.schema.metadata import Authority, Classification, EntityType
from pch_core.schema.project import Goal, OperationalPhase, Project, ProjectStatus
from pydantic import ValidationError


def _project(**extra):
    payload = {
        "id": "prj_1",
        "owner": "per_1",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "type": EntityType.PROJECT,
        "title": "Europe Trip",
        "classification": Classification.PERSONAL,
        "authority": Authority.USER_CONFIRMED,
    }
    payload.update(extra)
    return Project(**payload)


def _goal(**extra):
    payload = {
        "id": "goal_1",
        "owner": "per_1",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "type": EntityType.GOAL,
        "title": "Plan 10-day trip",
        "classification": Classification.PERSONAL,
        "authority": Authority.USER_CONFIRMED,
    }
    payload.update(extra)
    return Goal(**payload)


def test_operational_fields_default_null():
    project = _project()
    assert project.operational_phase is None
    assert project.current_step is None
    assert project.situation_intent is None
    goal = _goal()
    assert goal.operational_phase is None
    assert goal.current_step is None
    assert goal.situation_intent is None


def test_status_independent_of_phase():
    project = _project(status=ProjectStatus.ACTIVE, operational_phase=OperationalPhase.DECIDING)
    assert project.status == ProjectStatus.ACTIVE
    assert project.operational_phase == OperationalPhase.DECIDING


def test_unknown_phase_rejected():
    with pytest.raises(ValidationError):
        _project(operational_phase="comparing itineraries")
    with pytest.raises(ValidationError):
        _goal(operational_phase="kicking_off")


def test_step_and_intent_max_200():
    ok = "x" * 200
    _project(current_step=ok, situation_intent=ok)
    with pytest.raises(ValidationError):
        _project(current_step="x" * 201)
    with pytest.raises(ValidationError):
        _goal(situation_intent="y" * 201)


def test_situation_ref_optional_fields():
    ref = SituationRef(project_id="prj_1", title="Europe Trip", status="active")
    assert ref.operational_phase is None
    assert ref.current_step is None
    assert ref.situation_intent is None
    filled = SituationRef(
        project_id="prj_1",
        title="Europe Trip",
        status="active",
        operational_phase="deciding",
        current_step="rank two remaining itineraries",
        situation_intent="choose next itinerary",
    )
    assert filled.operational_phase == "deciding"
    assert filled.status == "active"

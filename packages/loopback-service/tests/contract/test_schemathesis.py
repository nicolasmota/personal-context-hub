import pytest


@pytest.mark.skip(reason="optional OpenAPI fuzz; enable with schemathesis extra")
def test_schemathesis_placeholder():
    assert True

import pytest

from app.services.llm.response_validator import ResponseValidator


def test_validator_parses_categories():
    result = ResponseValidator().categories('{"categories":{"t1":"Shopping"}}')

    assert result == {"t1": "Shopping"}


def test_validator_rejects_non_json_response():
    with pytest.raises(ValueError):
        ResponseValidator().narrative("not json")

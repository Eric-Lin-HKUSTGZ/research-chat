import pytest

from app.services.llm_service import get_prompt, construct_paper, LLMClient
from app.core.config import Config


def test_get_prompt_valid_and_invalid():
    out = get_prompt("retrieve_query", user_query="abc")
    assert "User Query: abc" in out
    with pytest.raises(ValueError):
        get_prompt("unknown_template")


def test_construct_paper_concatenates_titles_and_abstracts():
    newest = [{"title": "T1", "abstract": "A1"}]
    cited = [{"title": "T2", "abstract": "A2"}]
    relevant = [{"title": "T3", "abstract": "A3"}]
    paper = construct_paper(newest, cited, relevant)
    assert "The latest paper:" in paper and "Title: T1" in paper and "Abstract: A1" in paper
    assert "The highly cited paper:" in paper and "Title: T2" in paper
    assert "The relevent paper:" in paper and "Title: T3" in paper


def test_llm_client_config_info(monkeypatch):
    monkeypatch.setattr(Config, "CUSTOM_MODEL", "model-x")
    monkeypatch.setattr(Config, "CUSTOM_API_ENDPOINT", "http://localhost:1234/v1")
    monkeypatch.setattr(Config, "CUSTOM_API_KEY", "sk-test")

    client = LLMClient(provider="custom")
    info = client.get_config_info()
    assert info["provider"] == "custom"
    assert info["model"] == "model-x"
    assert info["endpoint"].startswith("http://localhost:1234")
    assert isinstance(info["temperature"], float)
    assert isinstance(info["max_retries"], int)

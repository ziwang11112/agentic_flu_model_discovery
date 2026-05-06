from __future__ import annotations

import pytest

from scripts.run_llm_v1_selected_repeats import REPO_ROOT, _assert_not_forbidden_output, _require_openai_api_key


def test_selected_repeat_guard_rejects_frozen_artifact_roots() -> None:
    with pytest.raises(RuntimeError, match="frozen artifact root"):
        _assert_not_forbidden_output(REPO_ROOT / "artifacts_llm_v1")


def test_selected_repeat_guard_allows_new_repeat_roots() -> None:
    _assert_not_forbidden_output(REPO_ROOT / "artifacts_llm_v1_openai_selected_repeats" / "run_1")


def test_selected_repeat_requires_openai_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is required"):
        _require_openai_api_key(load_dotenv=False)

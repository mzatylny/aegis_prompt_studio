from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_streamlit_app_renders_without_exceptions() -> None:
    app_path = (
        Path(__file__).parents[1] / "src" / "aegis_prompt_studio" / "ui.py"
    )
    app = AppTest.from_file(str(app_path)).run(timeout=15)
    assert not app.exception
    assert len(app.tabs) == 2
    assert app.tabs[0].label == "🛡️ Prompt Security Scanner"
    assert app.tabs[1].label == "🔎 Multi-Agent Research"


def test_ui_requires_user_key_before_exposing_tools(monkeypatch):
    from aegis_prompt_studio.config import get_settings

    monkeypatch.setattr(get_settings(), "api_access_key", "fixture-key")
    path = Path(__file__).parents[1] / "src/aegis_prompt_studio/ui.py"
    app = AppTest.from_file(str(path)).run(timeout=15)
    assert not app.exception
    assert not app.tabs
    assert app.text_input(key="access_key").value == ""
    app.text_input(key="access_key").set_value("wrong").run()
    assert not app.tabs
    app.text_input(key="access_key").set_value("fixture-key").run()
    assert len(app.tabs) == 2


def test_ui_sends_entered_key_to_protected_research_service(monkeypatch):
    from aegis_prompt_studio import api_client
    from aegis_prompt_studio.config import get_settings
    from aegis_prompt_studio.research.pipeline import ResearchPipeline

    settings = get_settings()
    monkeypatch.setattr(settings, "api_access_key", "fixture-key")
    calls = []

    def research(question, *, base_url, access_key):
        calls.append((base_url, access_key))
        return ResearchPipeline(settings).run(question)

    monkeypatch.setattr(api_client, "request_research", research)
    path = Path(__file__).parents[1] / "src/aegis_prompt_studio/ui.py"
    app = AppTest.from_file(str(path)).run(timeout=15)
    app.text_input(key="access_key").set_value("fixture-key").run()
    next(button for button in app.button if button.label == "Launch research workflow").click().run()
    assert not app.exception
    assert calls == [(settings.api_url, "fixture-key")]

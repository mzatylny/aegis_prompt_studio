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

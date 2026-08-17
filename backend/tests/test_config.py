import os

from app.config import load_local_env


def test_load_local_env_reads_simple_values_without_overriding(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# local only\nTEST_CH1_VALUE=loaded\nTEST_CH1_QUOTED='quoted value'\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("TEST_CH1_VALUE", raising=False)
    monkeypatch.setenv("TEST_CH1_QUOTED", "system value")

    load_local_env(env_file)

    assert os.environ["TEST_CH1_VALUE"] == "loaded"
    assert os.environ["TEST_CH1_QUOTED"] == "system value"


def test_load_local_env_ignores_missing_file(tmp_path):
    load_local_env(tmp_path / "missing.env")

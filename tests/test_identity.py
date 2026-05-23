from pathlib import Path

from zero_env_proxy.identity import extract_python_script_path


def test_extract_python_script_path_prefers_py_file(tmp_path: Path):
    script = tmp_path / "agent.py"
    script.write_text("print('ok')\n", encoding="utf-8")

    result = extract_python_script_path(["python", str(script)])

    assert result == script.resolve()


def test_extract_python_script_path_returns_none_without_script():
    assert extract_python_script_path(["python", "-m", "module"]) is None

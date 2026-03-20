from __future__ import annotations

import pytest

import main_interface


@pytest.mark.unit
def test_main_reports_actionable_qt_import_failures(tmp_path, monkeypatch, capsys):
    exe_dir = tmp_path / "Batch File Sender"
    exe_dir.mkdir()
    expected_log = exe_dir / "batch-file-sender-startup-error.log"

    def fake_import_module(name: str):
        if name == "interface.qt.app":
            raise ImportError("DLL load failed while importing QtWidgets")
        raise AssertionError(f"Unexpected import: {name}")

    monkeypatch.setattr(main_interface.importlib, "import_module", fake_import_module)
    monkeypatch.setattr(main_interface.sys, "frozen", True, raising=False)
    monkeypatch.setattr(
        main_interface.sys, "executable", str(exe_dir / "Batch File Sender.exe")
    )
    monkeypatch.setattr(
        main_interface.tempfile, "gettempdir", lambda: str(tmp_path / "temp")
    )

    with pytest.raises(SystemExit) as exc_info:
        main_interface.main()

    assert exc_info.value.code == 1

    captured = capsys.readouterr()
    assert "Qt runtime failed to load" in captured.err
    assert "DLL load failed while importing QtWidgets" in captured.err
    assert "Visual C++ 2015-2022 Redistributable (x64)" in captured.err
    assert "Keep the full extracted Batch File Sender bundle together" in captured.err
    assert "_internal/PyQt6/Qt6/bin" in captured.err
    assert "plugins/platforms/qwindows.dll" in captured.err
    assert f"Support log: {expected_log}" in captured.err

    assert expected_log.exists()
    log_text = expected_log.read_text(encoding="utf-8")
    assert "ImportError: DLL load failed while importing QtWidgets" in log_text
    assert "Traceback:" in log_text


@pytest.mark.unit
def test_main_preserves_normal_startup(monkeypatch):
    events: list[str] = []

    class FakeApp:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            events.append("init")

        def initialize(self):
            events.append("initialize")

        def run(self):
            events.append("run")
            return 0

        def shutdown(self):
            events.append("shutdown")

    monkeypatch.setattr(main_interface, "_load_qt_app_class", lambda: FakeApp)

    with pytest.raises(SystemExit) as exc_info:
        main_interface.main()

    assert exc_info.value.code == 0
    assert events == ["init", "initialize", "run", "shutdown"]

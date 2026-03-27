import pytest

import build_wine_local


@pytest.mark.unit
def test_dependency_reinstall_reason_accepts_matching_marker(tmp_path):
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("PyQt6==6.10.0\npytest==8.0.0\n", encoding="utf-8")
    marker_path = tmp_path / ".deps_installed_py311.txt"

    marker_path.write_text(
        "".join(
            f"{key}={value}\n"
            for key, value in build_wine_local.get_dependency_marker_metadata(
                req_file
            ).items()
        ),
        encoding="utf-8",
    )

    assert (
        build_wine_local.get_dependency_reinstall_reason(marker_path, req_file) is None
    )


@pytest.mark.unit
def test_dependency_reinstall_reason_detects_pyinstaller_pin_change(tmp_path):
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("PyQt6==6.10.0\n", encoding="utf-8")
    marker_path = tmp_path / ".deps_installed_py311.txt"
    metadata = build_wine_local.get_dependency_marker_metadata(req_file)

    marker_path.write_text(
        "".join(
            f"{key}={value}\n"
            for key, value in {
                **metadata,
                "pyinstaller": "6.11.0",
            }.items()
        ),
        encoding="utf-8",
    )

    reason = build_wine_local.get_dependency_reinstall_reason(marker_path, req_file)

    assert reason is not None
    assert "pyinstaller changed from 6.11.0" in reason
    assert build_wine_local.PYINSTALLER_VERSION in reason


@pytest.mark.unit
def test_install_dependencies_reinstalls_pyinstaller_when_marker_is_stale(
    tmp_path, monkeypatch
):
    project_root = tmp_path / "project"
    project_root.mkdir()
    req_file = project_root / "requirements.txt"
    req_file.write_text("PyQt6==6.10.0\npytest==8.0.0\n", encoding="utf-8")
    fake_script = project_root / "build_wine_local.py"
    fake_script.write_text("# test stub\n", encoding="utf-8")

    build_dir = tmp_path / "build_wine"
    build_dir.mkdir()
    marker_path = build_dir / ".deps_installed_py311.txt"
    marker_path.write_text(
        "python=3.11.9\npyinstaller=6.11.0\nrequirements_sha256=stale\n",
        encoding="utf-8",
    )

    python_dir = tmp_path / "python"
    scripts_dir = python_dir / "Scripts"
    scripts_dir.mkdir(parents=True)
    (python_dir / "python.exe").write_text("", encoding="utf-8")
    (scripts_dir / "pyinstaller.exe").write_text("", encoding="utf-8")

    calls = []

    def fake_run_wine(cmd, cwd=None, check=True, timeout=None):
        calls.append(cmd)

    monkeypatch.setattr(build_wine_local, "BUILD_DIR", build_dir)
    monkeypatch.setattr(build_wine_local, "DEPENDENCY_MARKER", marker_path)
    monkeypatch.setattr(build_wine_local, "__file__", str(fake_script))
    monkeypatch.setattr(build_wine_local, "run_wine", fake_run_wine)

    build_wine_local.install_dependencies(python_dir)

    assert len(calls) == 3
    assert calls[1] == [
        str(python_dir / "python.exe"),
        "-m",
        "pip",
        "install",
        "--upgrade",
        "--force-reinstall",
        f"pyinstaller=={build_wine_local.PYINSTALLER_VERSION}",
    ]

    assert marker_path.exists()
    marker_contents = marker_path.read_text(encoding="utf-8")
    assert f"pyinstaller={build_wine_local.PYINSTALLER_VERSION}" in marker_contents
    assert "requirements_sha256=" in marker_contents

    modified_requirements = build_dir / "requirements_modified.txt"
    assert modified_requirements.exists()
    assert "pytest==8.0.0" not in modified_requirements.read_text(encoding="utf-8")


@pytest.mark.unit
def test_install_dependencies_reuses_cache_when_marker_matches(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    project_root.mkdir()
    req_file = project_root / "requirements.txt"
    req_file.write_text("PyQt6==6.10.0\n", encoding="utf-8")
    fake_script = project_root / "build_wine_local.py"
    fake_script.write_text("# test stub\n", encoding="utf-8")

    build_dir = tmp_path / "build_wine"
    build_dir.mkdir()
    marker_path = build_dir / ".deps_installed_py311.txt"
    marker_path.write_text(
        "".join(
            f"{key}={value}\n"
            for key, value in build_wine_local.get_dependency_marker_metadata(
                req_file
            ).items()
        ),
        encoding="utf-8",
    )

    python_dir = tmp_path / "python"
    (python_dir / "Scripts").mkdir(parents=True)
    (python_dir / "python.exe").write_text("", encoding="utf-8")

    calls = []

    def fake_run_wine(cmd, cwd=None, check=True, timeout=None):
        calls.append(cmd)

    monkeypatch.setattr(build_wine_local, "BUILD_DIR", build_dir)
    monkeypatch.setattr(build_wine_local, "DEPENDENCY_MARKER", marker_path)
    monkeypatch.setattr(build_wine_local, "__file__", str(fake_script))
    monkeypatch.setattr(build_wine_local, "run_wine", fake_run_wine)

    build_wine_local.install_dependencies(python_dir)

    assert calls == []


@pytest.mark.unit
def test_write_windows_deployment_notes_creates_bundle_guidance(tmp_path):
    notes_path = build_wine_local.write_windows_deployment_notes(tmp_path)

    assert notes_path == tmp_path / build_wine_local.WINDOWS_DEPLOYMENT_NOTES_NAME
    notes_text = notes_path.read_text(encoding="utf-8")
    assert "Visual C++ 2015-2022 Redistributable (x64)" in notes_text
    assert "single-file executable" in notes_text
    assert build_wine_local.PYINSTALLER_VERSION in notes_text

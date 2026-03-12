"""Unit tests for scripts/run_tests.py."""

from types import SimpleNamespace

import scripts.run_tests as run_tests_script


def test_build_pytest_command_includes_expected_options():
    cmd = run_tests_script.build_pytest_command(
        marker="unit or fast",
        verbose=True,
        exitfirst=True,
        timeout=123,
        extra_args=["-k", "foo", "-q"],
    )

    assert cmd[:4] == [run_tests_script.sys.executable, "-m", "pytest", "tests"]
    assert cmd.count("-v") == 2
    assert "-x" in cmd
    assert ["-m", "unit or fast"] in [cmd[i : i + 2] for i in range(len(cmd) - 1)]
    assert cmd[cmd.index("--timeout") + 1] == "123"
    assert cmd[-3:] == ["-k", "foo", "-q"]


def test_build_pytest_command_without_optional_flags():
    cmd = run_tests_script.build_pytest_command(
        marker=None,
        verbose=False,
        exitfirst=False,
        timeout=300,
        extra_args=[],
    )

    assert cmd == [
        run_tests_script.sys.executable,
        "-m",
        "pytest",
        "tests",
        "-v",
        "--timeout",
        "300",
    ]


def test_run_tests_returns_subprocess_code(monkeypatch):
    args = SimpleNamespace(verbose=False, exitfirst=False, timeout=50)

    captured = {}

    def fake_build_pytest_command(marker, verbose, exitfirst, timeout, extra_args):
        captured["build"] = (marker, verbose, exitfirst, timeout, list(extra_args))
        return ["pytest-cmd"]

    def fake_run(cmd, check):
        captured["run"] = (list(cmd), check)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(
        run_tests_script, "build_pytest_command", fake_build_pytest_command
    )
    monkeypatch.setattr(run_tests_script.subprocess, "run", fake_run)

    result = run_tests_script.run_tests("unit", "Unit Tests", args, ["-k", "abc"])

    assert result == 0
    assert captured["build"] == ("unit", False, False, 50, ["-k", "abc"])
    assert captured["run"] == (["pytest-cmd"], False)


def test_run_tests_keyboard_interrupt_returns_130(monkeypatch):
    args = SimpleNamespace(verbose=False, exitfirst=False, timeout=50)
    monkeypatch.setattr(
        run_tests_script, "build_pytest_command", lambda **kwargs: ["pytest-cmd"]
    )

    def raise_interrupt(cmd, check):
        raise KeyboardInterrupt

    monkeypatch.setattr(run_tests_script.subprocess, "run", raise_interrupt)

    assert run_tests_script.run_tests("unit", "Unit Tests", args) == 130


def test_run_tests_exception_returns_1(monkeypatch):
    args = SimpleNamespace(verbose=False, exitfirst=False, timeout=50)
    monkeypatch.setattr(
        run_tests_script, "build_pytest_command", lambda **kwargs: ["pytest-cmd"]
    )

    def raise_exception(cmd, check):
        raise RuntimeError("boom")

    monkeypatch.setattr(run_tests_script.subprocess, "run", raise_exception)

    assert run_tests_script.run_tests("unit", "Unit Tests", args) == 1


def test_main_list_via_flag(monkeypatch):
    monkeypatch.setattr(
        run_tests_script.sys, "argv", ["run_tests.py", "unit", "--list"]
    )

    called = {"listed": False, "ran": False}
    monkeypatch.setattr(
        run_tests_script, "list_suites", lambda: called.__setitem__("listed", True)
    )
    monkeypatch.setattr(
        run_tests_script, "run_tests", lambda *a, **k: called.__setitem__("ran", True)
    )

    rc = run_tests_script.main()

    assert rc == 0
    assert called["listed"] is True
    assert called["ran"] is False


def test_main_list_via_suite_name(monkeypatch):
    monkeypatch.setattr(run_tests_script.sys, "argv", ["run_tests.py", "list"])

    called = {"listed": False}
    monkeypatch.setattr(
        run_tests_script, "list_suites", lambda: called.__setitem__("listed", True)
    )

    rc = run_tests_script.main()

    assert rc == 0
    assert called["listed"] is True


def test_main_routes_quick_suite(monkeypatch):
    monkeypatch.setattr(
        run_tests_script.sys,
        "argv",
        ["run_tests.py", "quick", "--timeout", "99", "--verbose", "-k", "foo"],
    )

    captured = {}

    def fake_run_tests(marker, description, args, extra_args=None):
        captured["marker"] = marker
        captured["description"] = description
        captured["args"] = args
        captured["extra_args"] = list(extra_args or [])
        return 7

    monkeypatch.setattr(run_tests_script, "run_tests", fake_run_tests)

    rc = run_tests_script.main()

    assert rc == 7
    assert captured["marker"] == "unit or fast"
    assert captured["description"] == "Quick Tests"
    assert captured["args"].timeout == 99
    assert captured["args"].verbose is True
    assert captured["extra_args"] == ["-k", "foo"]


def test_main_routes_ci_suite(monkeypatch):
    monkeypatch.setattr(run_tests_script.sys, "argv", ["run_tests.py", "ci"])

    captured = {}

    def fake_run_tests(marker, description, args, extra_args=None):
        captured["marker"] = marker
        captured["description"] = description
        captured["extra_args"] = list(extra_args or [])
        return 0

    monkeypatch.setattr(run_tests_script, "run_tests", fake_run_tests)

    rc = run_tests_script.main()

    assert rc == 0
    assert captured["marker"] == "not slow"
    assert captured["description"] == "CI Tests"
    assert captured["extra_args"] == []


def test_main_routes_named_suite(monkeypatch):
    monkeypatch.setattr(run_tests_script.sys, "argv", ["run_tests.py", "unit", "-x"])

    captured = {}

    def fake_run_tests(marker, description, args, extra_args=None):
        captured["marker"] = marker
        captured["description"] = description
        captured["exitfirst"] = args.exitfirst
        captured["extra_args"] = list(extra_args or [])
        return 11

    monkeypatch.setattr(run_tests_script, "run_tests", fake_run_tests)

    rc = run_tests_script.main()

    assert rc == 11
    assert captured["marker"] == "unit"
    assert captured["description"] == "Unit Tests"
    assert captured["exitfirst"] is True
    assert captured["extra_args"] == []

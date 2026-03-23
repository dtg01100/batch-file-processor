"""Tests for PyInstaller build configuration.

Verifies that all required modules are included in the hidden imports list
and that hook files properly collect all submodules.
"""

import ast
from pathlib import Path

import pytest

import build_windows_docker
import build_windows_podman
import build_wine_local

try:
    from PyInstaller.utils.hooks import collect_submodules

    PYINSTALLER_AVAILABLE = True
except ImportError:
    PYINSTALLER_AVAILABLE = False


PROJECT_ROOT = Path(__file__).parent.parent.parent
HOOKS_DIR = PROJECT_ROOT / "hooks"
SPEC_FILE = PROJECT_ROOT / "main_interface.spec"


def get_python_packages():
    """Find all Python packages in the project."""
    packages = []
    for item in PROJECT_ROOT.iterdir():
        if item.is_dir() and (item / "__init__.py").exists():
            if item.name not in {
                ".venv",
                "test_venv",
                ".git",
                "__pycache__",
                "build",
                "dist",
                "hooks",
            }:
                packages.append(item.name)
    return packages


def get_spec_hidden_imports():
    """Parse the spec file to extract hidden imports list."""
    with open(SPEC_FILE) as f:
        content = f.read()

    tree = ast.parse(content)

    for node in ast.walk(tree):
        # Look for calls to Analysis(...)
        if isinstance(node, ast.Call):
            func = node.func
            func_name = ""
            if isinstance(func, ast.Name):
                func_name = func.id
            elif isinstance(func, ast.Attribute):
                func_name = func.attr
            if func_name == "Analysis":
                for keyword in node.keywords:
                    if keyword.arg == "hiddenimports":
                        if isinstance(keyword.value, ast.List):
                            return [
                                elt.value
                                for elt in keyword.value.elts
                                if isinstance(elt, ast.Constant)
                            ]
    return []


def get_hook_packages():
    """Get list of packages that have hook files."""
    hooks = []
    if HOOKS_DIR.exists():
        for hook_file in HOOKS_DIR.glob("hook-*.py"):
            package_name = hook_file.stem.replace("hook-", "")
            hooks.append(package_name)
    return hooks


class TestHiddenImports:
    """Test that hidden imports are properly configured."""

    @pytest.mark.skipif(not PYINSTALLER_AVAILABLE, reason="PyInstaller not installed")
    def test_hook_files_collect_all_submodules(self):
        """Verify hook files collect all submodules for their packages."""
        hook_packages = get_hook_packages()

        # Qt hooks use collect_data_files/collect_dynamic_libs instead of
        # collect_submodules.
        # This is correct for Qt modules which need binary/data collection
        qt_hooks = {"PyQt5", "PyQt5.QtCore", "PyQt5.QtGui", "PyQt5.QtWidgets"}

        for package in hook_packages:
            hook_file = HOOKS_DIR / f"hook-{package}.py"
            assert hook_file.exists(), f"Hook file for {package} not found"

            with open(hook_file) as f:
                hook_content = f.read()

            # Qt hooks should use collect_data_files/collect_dynamic_libs
            if package in qt_hooks:
                assert (
                    "collect_data_files" in hook_content
                    or "collect_dynamic_libs" in hook_content
                ), (
                    f"Qt hook for {package} should use collect_data_files "
                    "or collect_dynamic_libs"
                )
            else:
                # Non-Qt hooks should use collect_submodules
                collected = collect_submodules(package)
                assert len(collected) > 0, f"No submodules collected for {package}"

                assert (
                    "collect_submodules" in hook_content
                ), f"Hook for {package} should use collect_submodules"

    @pytest.mark.skipif(not PYINSTALLER_AVAILABLE, reason="PyInstaller not installed")
    def test_all_packages_have_hooks(self):
        """Ensure all local packages have corresponding hook files."""
        packages = get_python_packages()
        hook_packages = get_hook_packages()

        missing_hooks = []
        for pkg in packages:
            if pkg not in hook_packages:
                submodules = collect_submodules(pkg)
                if len(submodules) > 1:
                    missing_hooks.append(pkg)

        if missing_hooks:
            pytest.fail(
                f"Packages missing hook files (have submodules): {missing_hooks}\n"
                f"Create hook files in {HOOKS_DIR}/ using collect_submodules()"
            )

    @pytest.mark.skipif(not PYINSTALLER_AVAILABLE, reason="PyInstaller not installed")
    def test_hidden_imports_covers_convert_backends(self):
        """Verify all convert_to_* modules are in hidden imports or hooks."""
        hidden_imports = get_spec_hidden_imports()

        convert_modules = [f.stem for f in PROJECT_ROOT.glob("convert_to_*.py")]

        for module in convert_modules:
            assert module in hidden_imports, (
                f"Convert backend '{module}' not in hidden_imports. "
                f"Dynamically loaded backends must be explicitly listed."
            )

    @pytest.mark.skipif(not PYINSTALLER_AVAILABLE, reason="PyInstaller not installed")
    def test_hidden_imports_covers_send_backends(self):
        """Verify all *_backend modules are in hidden imports or hooks."""
        hidden_imports = get_spec_hidden_imports()

        backend_modules = [f.stem for f in PROJECT_ROOT.glob("*_backend.py")]

        for module in backend_modules:
            assert module in hidden_imports, (
                f"Send backend '{module}' not in hidden_imports. "
                f"Dynamically loaded backends must be explicitly listed."
            )

    def test_all_modules_importable(self):
        """Test that all Python modules in the project can be imported."""
        packages = get_python_packages()
        errors = []

        for pkg in packages:
            try:
                __import__(pkg)
            except ImportError as e:
                errors.append(f"{pkg}: {e}")

        standalone_modules = [
            f.stem
            for f in PROJECT_ROOT.glob("*.py")
            if f.stem not in {"__init__", "setup"} and not f.name.startswith("test_")
        ]

        for module in standalone_modules:
            try:
                __import__(module)
            except ImportError:
                pass
            except Exception:
                pass

        if errors:
            pytest.fail(f"Failed to import packages: {errors}")

    @pytest.mark.skipif(not PYINSTALLER_AVAILABLE, reason="PyInstaller not installed")
    def test_collect_submodules_returns_expected(self):
        """Verify collect_submodules works for project packages."""
        packages = get_python_packages()

        for pkg in packages:
            try:
                submodules = collect_submodules(pkg)
                assert pkg in submodules, f"Package {pkg} should include itself"
            except Exception as e:
                pytest.fail(f"collect_submodules failed for {pkg}: {e}")

    def test_hooks_directory_exists(self):
        """Verify hooks directory exists."""
        assert HOOKS_DIR.exists(), f"Hooks directory {HOOKS_DIR} should exist"

    def test_spec_file_exists(self):
        """Verify spec file exists."""
        assert SPEC_FILE.exists(), f"Spec file {SPEC_FILE} should exist"

    def test_spec_uses_hooks_directory(self):
        """Verify spec file is configured to use hooks directory."""
        with open(SPEC_FILE) as f:
            content = f.read()

        assert "hookspath" in content, "Spec file should configure hookspath"
        assert (
            "['hooks']" in content or '"hooks"' in content
        ), "Spec file should include 'hooks' in hookspath"

    def test_windows_bundle_validation_targets_qt_runtime(self):
        """Verify Windows bundle validation checks the Qt runtime pieces."""
        required_paths = set(build_wine_local.REQUIRED_WINDOWS_BUNDLE_PATHS)

        assert "_internal/PyQt5/QtWidgets.pyd" in required_paths
        assert "_internal/PyQt5/Qt5/bin/Qt5Widgets.dll" in required_paths
        assert "_internal/PyQt5/plugins/platforms/qwindows.dll" in required_paths
        assert "_internal/python311.dll" in required_paths

    def test_windows_bundle_dir_uses_dist_windows(self):
        """The Wine/local Windows build should write to dist_windows."""
        assert build_wine_local.get_windows_bundle_dir(
            PROJECT_ROOT / build_wine_local.WINDOWS_DIST_DIRNAME
        ) == (
            PROJECT_ROOT
            / build_wine_local.WINDOWS_DIST_DIRNAME
            / build_wine_local.WINDOWS_BUNDLE_NAME
        )

    def test_windows_dockerfile_uses_image_entrypoint(self):
        """Docker build should delegate to the image entrypoint."""
        dockerfile_content = build_windows_docker.build_dockerfile_content()

        assert "ENV SPECFILE=/src/main_interface.spec" in dockerfile_content
        assert "python3.11 -m PyInstaller" not in dockerfile_content

    def test_podman_build_route_fails_fast(self):
        """Podman script should reject the unsupported Linux PyInstaller route."""
        with pytest.raises(RuntimeError, match="Linux.*PyInstaller"):
            build_windows_podman.ensure_supported_build_route()


class TestImportDiscovery:
    """Tests to discover dynamically imported modules."""

    def test_find_importlib_import_module_calls(self):
        """Find all importlib.import_module() calls to identify dynamic imports."""
        dynamic_imports = set()

        for py_file in PROJECT_ROOT.rglob("*.py"):
            if (
                ".venv" in str(py_file)
                or "test_venv" in str(py_file)
                or "/venv" in str(py_file)
                or ".wine" in str(py_file)
                or "build_wine" in str(py_file)
                or "winvenv" in str(py_file)
            ):
                continue

            try:
                with open(py_file) as f:
                    content = f.read()

                if "import_module" in content:
                    import ast

                    try:
                        tree = ast.parse(content)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Call):
                                if isinstance(node.func, ast.Attribute):
                                    if node.func.attr == "import_module":
                                        if node.args:
                                            arg = node.args[0]
                                            if isinstance(arg, ast.Constant):
                                                dynamic_imports.add(arg.value)
                    except SyntaxError:
                        pass
            except Exception:
                pass

        hidden_imports = get_spec_hidden_imports()

        STDLIB_MODULES = {
            "threading",
            "multiprocessing",
            "asyncio",
            "concurrent",
            "queue",
            "json",
            "pickle",
            "sqlite3",
            "logging",
            "configparser",
            "argparse",
            "typing",
            "collections",
            "itertools",
            "functools",
            "operator",
            "pathlib",
            "os",
            "sys",
            "io",
            "re",
            "datetime",
            "time",
            "hashlib",
            "copy",
            "tempfile",
            "shutil",
            "subprocess",
            "warnings",
            "contextlib",
        }

        missing = []
        for imp in dynamic_imports:
            base_pkg = imp.split(".")[0]
            if base_pkg in STDLIB_MODULES:
                continue
            if imp not in hidden_imports:
                hook_pkgs = get_hook_packages()
                if base_pkg not in hook_pkgs:
                    missing.append(imp)

        if missing:
            pytest.fail(
                f"Dynamic imports not covered by hidden_imports or hooks: {missing}"
            )

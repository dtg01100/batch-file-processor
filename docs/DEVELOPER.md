Developer setup and commands

- Install dependencies: python -m pip install --upgrade pip && pip install -r requirements.txt
- Run tests: pytest -q
- Lint with ruff: ruff check .
- Check formatting with black: black --check .
- Package install for development: pip install -e .[dev]

Notes

A compatibility package batch_file_processor/__init__.py was added to expose top-level modules as package submodules to ease migration to package imports.
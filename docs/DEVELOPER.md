Developer setup and commands

- Install dependencies: python -m pip install --upgrade pip && pip install -r requirements.txt
- Run tests: pytest -q
- Lint with ruff: ruff check .
- Check formatting with black: black --check .
- Package install for development: pip install -e .[dev]

## Plugin Architecture

The application uses a modular plugin architecture for configuration management. For detailed documentation:

- [Plugin Architecture Overview](PLUGIN_ARCHITECTURE.md) - Core concepts and component overview
- [Plugin Developer Guide](PLUGIN_DEVELOPER_GUIDE.md) - How to create custom configuration plugins
- [Edit Folders Dialog Design](../docs/design/EDIT_FOLDERS_DIALOG_DESIGN.md) - Integration with the UI

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| PluginBase | `interface/plugins/plugin_base.py` | Base interface for all plugins |
| ConfigurationPlugin | `interface/plugins/configuration_plugin.py` | Format-specific configuration |
| PluginManager | `interface/plugins/plugin_manager.py` | Plugin discovery and lifecycle |
| SectionRegistry | `interface/plugins/section_registry.py` | UI section management |
| FormGenerator | `interface/form/form_generator.py` | Dynamic form generation |
| ConfigSchemas | `interface/plugins/config_schemas.py` | Field definitions and validation |

Notes

A compatibility package batch_file_processor/__init__.py was added to expose top-level modules as package submodules to ease migration to package imports.
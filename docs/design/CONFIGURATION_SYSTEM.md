# Configuration System Design Document

**Version:** 1.0  
**Date:** 2026-05-18  
**Status:** DRAFT

---

## 1. Overview

The configuration system manages global settings and per-folder plugin configurations.

## 2. Configuration Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    GUI Forms                                 │
│   (EditFoldersDialog, EditSettingsDialog)                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Plugin Configuration                      │
│   (ConfigurationPlugin, SectionRegistry, FormGenerator)      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Operations Layer                          │
│   (FolderManager, PluginConfigurationMapper)                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Database Tables                           │
│   (folders, settings)                                      │
└─────────────────────────────────────────────────────────────┘
```

## 3. Global Settings

**Table:** `settings`

```python
# interface/qt/dialogs/edit_settings_dialog.py
class EditSettingsDialog(QWidget):
    """Dialog for editing global application settings."""

    # Email
    enable_email: bool
    email_address: str
    email_username: str
    email_password: str  # Stored as-is (consider encryption)
    email_smtp_server: str
    email_smtp_port: int
    # ... additional settings
```

## 4. Folder Configuration

**Table:** `folders`

```python
# interface/models/folder_configuration.py
@dataclass
class FolderConfiguration:
    """Complete folder configuration data model."""

    # Identity
    folder_name: str = ""
    folder_is_active: bool = False
    alias: str = ""

    # Backend toggles
    process_backend_copy: bool = False
    process_backend_ftp: bool = False
    process_backend_email: bool = False
    process_backend_http: bool = False

    # Alerting
    alert_on_failure: bool = True

    # Backend configurations
    ftp: FTPConfiguration | None = None
    email: EmailConfiguration | None = None
    copy: CopyConfiguration | None = None
    http: HTTPConfiguration | None = None

    # EDI
    edi: EDIConfiguration | None = None        # process_edi, split_edi, tweak_edi, convert_to_format, etc.

    # UPC Override
    upc_override: UPCOverrideConfiguration | None = None

    # A-Record
    a_record_padding: ARecordPaddingConfiguration | None = None

    # Invoice Date
    invoice_date: InvoiceDateConfiguration | None = None

    # Backend-specific
    backend_specific: BackendSpecificConfiguration | None = None

    # CSV
    csv: CSVConfiguration | None = None

    # Plugin configurations (per-format, persisted as JSON)
    plugin_configurations: dict[str, dict[str, Any]] = field(default_factory=dict)
```

## 5. Plugin Configuration

### 5.1 PluginConfig Structure

```python
# interface/plugins/plugin_config.py
@dataclass
class PluginConfig:
    plugin_name: str
    parameters: Dict[str, Any]
```

### 5.2 Serialization

Plugin configurations are serialized to JSON:

```json
{
    "scannerware": {
        "include_header": true,
        "field_delimiter": ",",
        "date_format": "YYYYMMDD"
    }
}
```

### 5.3 Plugin Manager

```python
# interface/plugins/plugin_manager.py
class PluginManager:
    def get_plugin(self, format_name: str) -> ConfigurationPlugin:
        """Get configuration plugin by format."""

    def get_configuration_plugins(self) -> list[ConfigurationPlugin]:
        """Get all available configuration plugins."""

    def register_plugin(self, plugin: ConfigurationPlugin) -> None:
        """Register custom plugin."""
```

## 6. Section Registry

**Module:** `interface/plugins/section_registry.py`

```python
class SectionRegistry:
    """Registry of section types for form generation."""
    
    SECTIONS = {
        'general': GeneralSection,
        'converter': ConverterSection,
        'backend': BackendSection,
        'tweaks': TweaksSection,
    }
```

## 7. Form Generation

**Module:** `interface/form/form_generator.py`

```python
class FormGenerator:
    def generate_form(self, plugin: ConfigurationPlugin) -> List[QWidget]:
        """Generate Qt widgets from plugin configuration."""
        sections = plugin.get_sections()
        widgets = []
        for section in sections:
            section_widget = self._create_section(section)
            widgets.append(section_widget)
        return widgets
    
    def _create_section(self, section: ConfigSection) -> QWidget:
        """Create widget for a configuration section."""
        group = QGroupBox(section.title)
        layout = QVBoxLayout()
        for field in section.fields:
            widget = self._create_field_widget(field)
            layout.addWidget(widget)
        group.setLayout(layout)
        return group
```

## 8. Validation

**Module:** `interface/validation/folder_settings_validator.py`

```python
class FolderSettingsValidator:
    def validate(self, values: dict) -> List[ValidationError]:
        """Validate folder configuration values."""
        errors = []
        
        # Required fields
        if not values.get('folder_name'):
            errors.append(ValidationError('folder_name', 'Required'))
        
        # Path validation
        path = values.get('folder_path')
        if path and not os.path.isdir(path):
            errors.append(ValidationError('folder_path', 'Directory not found'))
        
        # Backend validation
        backends = values.get('folder_backends', [])
        if 'email' in backends and not settings.get('enable_email'):
            errors.append(ValidationError('folder_backends', 'Email not enabled'))
        
        return errors
```

## 9. Configuration Export/Import

### 9.1 Export

```python
def export_configuration(db_path: str, output_path: str):
    """Export folder configurations to JSON."""
    from database.database_obj import DatabaseObj

    with DatabaseObj(db_path) as db:
        folders = db['folders'].find()
    with open(output_path, 'w') as f:
        json.dump(folders, f, indent=2)
```

### 9.2 Import

```python
def import_configuration(db_path: str, input_path: str):
    """Import folder configurations from JSON."""
    from database.database_obj import DatabaseObj

    with open(input_path) as f:
        folders = json.load(f)
    with DatabaseObj(db_path) as db:
        for folder in folders:
            db['folders'].insert(folder)
```

## 10. Related Documents

- [GUI_ARCHITECTURE.md](GUI_ARCHITECTURE.md) - GUI design
- [DIALOG_DESIGN.md](DIALOG_DESIGN.md) - Dialog components
- [PLUGIN_API.md](PLUGIN_API.md) - Plugin interfaces
- [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) - Database design

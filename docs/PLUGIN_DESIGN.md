# Plugin System Design Document

**Generated:** 2026-01-30  
**Commit:** c2898be44  
**Branch:** cleanup-refactoring

## 1. Overview

The plugin system provides extensibility for adding new converters and send backends without modifying core application code. Plugins are discovered dynamically at runtime based on file naming conventions.

## 2. Plugin Types

### 2.1 Converter Plugins

Convert EDI files to various output formats.

**Location:** Root directory (`convert_to_*.py`)  
**Pattern:** `convert_to_<format>.py`  
**Count:** 10 plugins

**Existing Converters:**
| Plugin ID | File | Description |
|-----------|------|-------------|
| `csv` | `convert_to_csv.py` | Standard CSV format |
| `simplified_csv` | `convert_to_simplified_csv.py` | Simplified CSV output |
| `fintech` | `convert_to_fintech.py` | Fintech format |
| `scannerware` | `convert_to_scannerware.py` | Scannerware format |
| `scansheet_type_a` | `convert_to_scansheet_type_a.py` | Scansheet type A |
| `estore_einvoice` | `convert_to_estore_einvoice.py` | eStore eInvoice |
| `estore_einvoice_generic` | `convert_to_estore_einvoice_generic.py` | eStore generic eInvoice |
| `jolley_custom` | `convert_to_jolley_custom.py` | Jolley custom format |
| `stewarts_custom` | `convert_to_stewarts_custom.py` | Stewart's custom format |
| `yellowdog_csv` | `convert_to_yellowdog_csv.py` | Yellowdog CSV format |

### 2.2 Send Backend Plugins

Send processed files to various destinations.

**Location:** Root directory (`*_backend.py`)  
**Pattern:** `<name>_backend.py`  
**Count:** 3 plugins

**Existing Backends:**
| Plugin ID | File | Description |
|-----------|------|-------------|
| `copy` | `copy_backend.py` | Copy to local directory |
| `ftp` | `ftp_backend.py` | FTP transfer with TLS |
| `email` | `email_backend.py` | Email via SMTP |

## 3. Plugin Discovery Mechanism

### 3.1 Dynamic Import

Plugins are discovered using Python's `importlib` module:

```python
# Converter discovery
module_name = "convert_to_" + format.lower().replace(" ", "_").replace("-", "_")
module = importlib.import_module(module_name)

# Backend discovery
module_name = f"{backend_name}_backend"
backend = importlib.import_module(module_name)
```

### 3.2 Plugin Registry

```python
# plugin_config.py
class PluginRegistry:
    @staticmethod
    def discover_plugins(plugin_type: str) -> List[Dict]:
        """Discover available plugins of a given type."""
        pass
```

## 4. Converter Plugin Architecture

### 4.1 Base Class

```python
# convert_base.py
class BaseConverter:
    PLUGIN_ID = "base"
    PLUGIN_NAME = "Base Converter"
    PLUGIN_DESCRIPTION = "Base class for converters"
    CONFIG_FIELDS = []
    
    def __init__(self, edi_process: str, output_filename: str, 
                 settings_dict: dict, parameters_dict: dict, upc_lookup: dict):
        self.edi_process = edi_process
        self.output_filename = output_filename
        self.settings_dict = settings_dict
        self.parameters_dict = parameters_dict
        self.upc_lookup = upc_lookup
    
    def initialize_output(self) -> None:
        """Initialize output file/stream."""
        pass
    
    def process_record_a(self, record: dict) -> None:
        """Process A record (invoice header)."""
        pass
    
    def process_record_b(self, record: dict) -> None:
        """Process B record (line item)."""
        pass
    
    def process_record_c(self, record: dict) -> None:
        """Process C record (charge/adjustment)."""
        pass
    
    def finalize_output(self) -> None:
        """Finalize output file/stream."""
        pass
```

### 4.2 CSV Converter Example

```python
# convert_to_csv.py
class CsvConverter(CSVConverter):
    PLUGIN_ID = "csv"
    PLUGIN_NAME = "Standard CSV"
    PLUGIN_DESCRIPTION = "Basic CSV format with UPC, quantity, cost, retail, description, case pack, and item number"
    
    CONFIG_FIELDS = [
        {
            "key": "include_headers",
            "label": "Include Headers",
            "type": "boolean",
            "default": False,
        },
        {
            "key": "calculate_upc_check_digit",
            "label": "Calculate UPC Check Digit",
            "type": "boolean",
            "default": False,
        },
        # ... more fields
    ]
    
    def initialize_output(self) -> None:
        super().initialize_output()
        if self.inc_headers:
            self.write_header(["UPC", "Qty. Shipped", "Cost", ...])
    
    def process_record_b(self, record: dict) -> None:
        # Transform record data
        upc = self.process_upc(record["upc_number"], calc_check_digit=True)
        # Write row
        self.write_row([upc, record["qty_of_units"], ...])
```

### 4.3 EDI Record Types

Converters handle three standard EDI record types:

| Record | Type | Content |
|--------|------|---------|
| A | Header | Invoice metadata (number, date, total) |
| B | Line Item | Product info (UPC, quantity, price, description) |
| C | Charge | Adjustments, taxes, fees |

### 4.4 Wrapper Function

```python
# convert_base.py
def create_edi_convert_wrapper(converter_class):
    """Create the edi_convert function for a converter."""
    
    def edi_convert(input_file: str, output_file: str, settings: dict,
                   parameters_dict: dict, upc_dict: dict) -> str:
        converter = converter_class(
            edi_process="edi_convert",
            output_filename=output_file,
            settings_dict=settings,
            parameters_dict=parameters_dict,
            upc_lookup=upc_dict,
        )
        converter.process(input_file)
        return converter.output_filename
    
    return edi_convert
```

## 5. Send Backend Plugin Architecture

### 5.1 Base Class

```python
# send_base.py
class BaseSendBackend:
    PLUGIN_ID = "base"
    PLUGIN_NAME = "Base Backend"
    PLUGIN_DESCRIPTION = "Base class for send backends"
    CONFIG_FIELDS = []
    
    def __init__(self, process_parameters: dict, settings_dict: dict, filename: str):
        self.process_parameters = process_parameters
        self.settings_dict = settings_dict
        self.filename = filename
    
    def get_config_value(self, key: str, default=None):
        """Get configuration value from plugin config or process parameters."""
        # Check plugin-specific config
        plugin_config = self.process_parameters.get("plugin_config")
        if plugin_config and isinstance(plugin_config, dict):
            if key in plugin_config:
                return plugin_config[key]
        # Fall back to process parameters
        return self.process_parameters.get(key, default)
    
    def _send(self) -> None:
        """Implement sending logic in subclass."""
        raise NotImplementedError
```

### 5.2 Copy Backend Example

```python
# copy_backend.py
class CopySendBackend(BaseSendBackend):
    PLUGIN_ID = "copy"
    PLUGIN_NAME = "Copy to Directory"
    PLUGIN_DESCRIPTION = "Copy files to a local directory"
    
    CONFIG_FIELDS = [
        {
            "key": "copy_to_directory",
            "label": "Destination Directory",
            "type": "string",
            "default": "",
            "required": True,
        }
    ]
    
    def _send(self):
        dest_dir = self.get_config_value("copy_to_directory", "")
        shutil.copy(self.filename, dest_dir)
```

### 5.3 FTP Backend Example

```python
# ftp_backend.py
class FTPSendBackend(BaseSendBackend):
    PLUGIN_ID = "ftp"
    PLUGIN_NAME = "FTP Transfer"
    PLUGIN_DESCRIPTION = "Send files via FTP with TLS fallback"
    
    CONFIG_FIELDS = [
        {
            "key": "ftp_server",
            "label": "FTP Server",
            "type": "string",
            "required": True,
        },
        {
            "key": "ftp_port",
            "label": "FTP Port",
            "type": "integer",
            "default": 21,
        },
        # ... more fields
    ]
    
    def _send(self):
        with open(self.filename, "rb") as send_file:
            ftp_providers = [ftplib.FTP_TLS, ftplib.FTP]
            for provider in ftp_providers:
                ftp = provider()
                try:
                    ftp.connect(self.get_config_value("ftp_server"), ...)
                    ftp.login(...)
                    ftp.storbinary("stor " + self.get_config_value("ftp_folder") + filename, send_file)
                    break
                except Exception:
                    # Try next provider
                    pass
```

### 5.4 Email Backend Example

```python
# email_backend.py
class EmailSendBackend(BaseSendBackend):
    PLUGIN_ID = "email"
    PLUGIN_NAME = "Email Delivery"
    PLUGIN_DESCRIPTION = "Send files via email using SMTP"
    
    CONFIG_FIELDS = [
        {
            "key": "email_to",
            "label": "Email Recipient",
            "type": "string",
            "required": True,
        },
        {
            "key": "email_subject_line",
            "label": "Email Subject",
            "type": "string",
            "default": "%filename% Attached - %datetime%",
        },
    ]
    
    def _send(self):
        message = EmailMessage()
        message["Subject"] = self.get_config_value("email_subject_line", ...)
        message["From"] = self.settings_dict["email_address"]
        message["To"] = self.get_config_value("email_to", "").split(", ")
        
        with open(self.filename, "rb") as fp:
            message.add_attachment(fp.read(), filename=os.path.basename(self.filename))
        
        server = smtplib.SMTP(
            self.settings_dict["email_smtp_server"],
            self.settings_dict["smtp_port"],
        )
        server.send_message(message)
        server.close()
```

### 5.5 Wrapper Function

```python
# send_base.py
def create_send_wrapper(backend_class):
    """Create the do function for a backend."""
    
    def do(process_parameters: dict, settings_dict: dict, filename: str):
        backend = backend_class(process_parameters, settings_dict, filename)
        return backend._send()
    
    return do
```

## 6. Configuration Fields

### 6.1 Field Schema

```python
CONFIG_FIELDS = [
    {
        "key": "field_name",           # Unique identifier
        "label": "Display Label",      # UI label
        "type": "string | integer | boolean",
        "default": value,              # Default value
        "required": False,             # Whether required
        "placeholder": "text",         # Placeholder text
        "help": "Help text",           # Help tooltip
        "min_value": 1,                # For integers
        "max_value": 100,              # For integers
    }
]
```

### 6.2 Dynamic UI Generation

```python
# interface/ui/plugin_ui_generator.py
def build_plugin_ui(config_fields: List[dict]) -> QWidget:
    """Build UI widget from configuration fields."""
    widget = QWidget()
    layout = QFormLayout()
    
    for field in config_fields:
        if field["type"] == "string":
            input_widget = QLineEdit()
            input_widget.setPlaceholderText(field.get("placeholder", ""))
        elif field["type"] == "boolean":
            input_widget = QCheckBox()
        elif field["type"] == "integer":
            input_widget = QSpinBox()
            input_widget.setMinimum(field.get("min_value", 0))
            input_widget.setMaximum(field.get("max_value", 9999))
        
        layout.addRow(field["label"], input_widget)
    
    return widget
```

## 7. Plugin Configuration Storage

### 7.1 Database Storage

Plugin configuration is stored in the `folders` table:

```python
# Folder configuration includes:
"plugin_config": None,  # JSON serialized plugin configuration
```

### 7.2 Configuration Access

```python
def get_config_value(self, key: str, default=None):
    plugin_config = self.process_parameters.get("plugin_config")
    if plugin_config and isinstance(plugin_config, dict):
        if key in plugin_config:
            return plugin_config[key]
    return self.process_parameters.get(key, default)
```

## 8. Plugin Development Guide

### 8.1 Creating a New Converter

1. Create file `convert_to_myformat.py`:

```python
from convert_base import BaseConverter, create_edi_convert_wrapper

class MyFormatConverter(BaseConverter):
    PLUGIN_ID = "myformat"
    PLUGIN_NAME = "My Format"
    PLUGIN_DESCRIPTION = "Description of my format"
    CONFIG_FIELDS = []
    
    def initialize_output(self) -> None:
        # Open output file, write headers
        pass
    
    def process_record_a(self, record: dict) -> None:
        # Process header record
        pass
    
    def process_record_b(self, record: dict) -> None:
        # Process line item record
        pass
    
    def process_record_c(self, record: dict) -> None:
        # Process charge record
        pass
    
    def finalize_output(self) -> None:
        # Close output file
        pass

edi_convert = create_edi_convert_wrapper(MyFormatConverter)
```

2. Add tests in `tests/convert_backends/`

### 8.2 Creating a New Backend

1. Create file `mybackend_backend.py`:

```python
from send_base import BaseSendBackend, create_send_wrapper

class MyBackend(BaseSendBackend):
    PLUGIN_ID = "mybackend"
    PLUGIN_NAME = "My Backend"
    PLUGIN_DESCRIPTION = "Description of my backend"
    CONFIG_FIELDS = []
    
    def _send(self):
        # Implement sending logic
        pass

do = create_send_wrapper(MyBackend)
```

2. Register in `dispatch/send_manager.py`:

```python
class SendManager:
    BACKEND_CONFIG = {
        'mybackend': ('mybackend_backend', 'config_key', 'Display Name'),
        ...
    }
```

## 9. Testing

### 9.1 Converter Testing

```python
# tests/convert_backends/test_parity_verification.py
def test_converter_parity():
    """Test converter output matches baseline."""
    for converter_id in CONVERTER_IDS:
        # Run converter on test data
        # Compare output to baseline
        assert output == baseline
```

### 9.2 Backend Testing

```python
# tests/unit/test_backends.py
def test_email_backend():
    backend = EmailSendBackend({}, settings, "test_file.txt")
    # Test sending
```

## 10. Best Practices

### 10.1 Converter Guidelines

- Inherit from appropriate base class (`CSVConverter`, `DBEnabledConverter`)
- Handle all three record types (A, B, C)
- Use `process_upc()` for UPC processing
- Use `apply_upc_override()` for UPC lookup
- Use `apply_retail_uom_transform()` for retail UOM

### 10.2 Backend Guidelines

- Implement exponential backoff for network operations
- Handle connection failures gracefully
- Use TLS for secure connections when available
- Log errors with meaningful messages

### 10.3 Configuration Guidelines

- Use descriptive keys
- Provide sensible defaults
- Include help text for complex options
- Validate inputs in `validate()` method if using dialogs

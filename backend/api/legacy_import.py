"""
Legacy configuration import API
Converts legacy folders.db configurations to new pipeline format
"""

import json
import sqlite3
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
import tempfile
import os
from pathlib import Path

from backend.core.database import get_database
from backend.models.pipeline import PipelineCreate, PipelineUpdate

router = APIRouter(prefix="/api/legacy-import", tags=["legacy-import"])

class ImportResult(BaseModel):
    success: bool
    message: str
    imported_pipelines: int
    errors: List[str]

class PipelinePreview(BaseModel):
    id: str
    name: str
    description: str
    node_count: int
    has_errors: bool
    error_message: Optional[str] = None

def parse_legacy_folder_config(folder_row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse legacy folder configuration and convert to pipeline format
    """
    try:
        # Extract basic info
        folder_name = folder_row.get("folder_name", "")
        alias = folder_row.get("alias", "Untitled Pipeline")
        enabled = folder_row.get("enabled", "False") == "True"

        # Determine connection type and parameters
        connection_type = folder_row.get("connection_type", "local")
        connection_params_str = folder_row.get("connection_params", "{}")

        try:
            connection_params = json.loads(connection_params_str) if connection_params_str else {}
        except json.JSONDecodeError:
            connection_params = {}

        # Create pipeline structure
        pipeline_data = {
            "name": alias,
            "description": f"Imported from legacy folder: {folder_name}",
            "nodes": [],
            "edges": [],
            "is_active": enabled
        }

        # Create input source node
        input_node = {
            "id": "input_source_1",
            "type": "folderSource",
            "position": {"x": 100, "y": 100},
            "data": {
                "id": "input_source_1",
                "label": "Input Source",
                "protocol": connection_type,
                "config": json.dumps(connection_params),
                "filePattern": determine_file_pattern(folder_row)  # Determine from legacy config
            }
        }

        # Create output node based on legacy processing settings
        output_node = {
            "id": "output_destination_1",
            "type": "output",
            "position": {"x": 700, "y": 100},
            "data": {
                "id": "output_destination_1",
                "label": "Output Destination",
                "protocol": determine_output_protocol(folder_row),
                "config": json.dumps(determine_output_config(folder_row))
            }
        }

        pipeline_data["nodes"] = [input_node, output_node]
        pipeline_data["edges"] = []

        # Add additional nodes based on legacy processing flags
        nodes = pipeline_data["nodes"]
        edges = pipeline_data["edges"]

        # Add processing nodes based on legacy settings
        current_x = 300
        current_node_id = "input_source_1"

        # Check for various processing flags from legacy database
        process_edi = folder_row.get("process_edi", "False") == "True"
        convert_to_format = folder_row.get("convert_to_format", "")
        tweak_edi = folder_row.get("tweak_edi", "False") == "True"
        split_edi = folder_row.get("split_edi", "False") == "True"
        force_edi_validation = folder_row.get("force_edi_validation", 0) == 1
        append_a_records = folder_row.get("append_a_records", "False") == "True"
        invoice_date_offset = folder_row.get("invoice_date_offset", 0)
        retail_uom = folder_row.get("retail_uom", 0)
        force_each_upc = folder_row.get("force_each_upc", 0) == 1
        include_item_numbers = folder_row.get("include_item_numbers", 0) == 1
        include_item_description = folder_row.get("include_item_description", 0) == 1

        # Add trigger node based on schedule
        schedule = folder_row.get("schedule", "")
        if schedule:
            trigger_node = {
                "id": f"trigger_{len(nodes)+1}",
                "type": "trigger",
                "position": {"x": current_x, "y": 100},
                "data": {
                    "id": f"trigger_{len(nodes)+1}",
                    "label": "Scheduled Trigger",
                    "triggerType": "scheduled",
                    "config": json.dumps({"schedule": schedule})
                }
            }
            nodes.append(trigger_node)

            # Add edge from input to trigger
            edges.append({
                "id": f"edge_input_to_trigger",
                "source": "input_source_1",
                "target": f"trigger_{len(nodes)-1}",
                "type": "smoothstep",
                "animated": True
            })

            current_node_id = f"trigger_{len(nodes)-1}"
            current_x += 200

        # EDI Processing node
        if process_edi or convert_to_format:
            transform_node = {
                "id": f"transform_{len(nodes)+1}",
                "type": "transform",
                "position": {"x": current_x, "y": 100},
                "data": {
                    "id": f"transform_{len(nodes)+1}",
                    "label": f"Convert to {convert_to_format.upper() if convert_to_format else 'EDI'}",
                    "transformations": json.dumps([{
                        "type": "convert_format",
                        "format": convert_to_format or "edi",
                        "process_edi": process_edi
                    }])
                }
            }
            nodes.append(transform_node)

            # Add edge from previous node to transform
            edges.append({
                "id": f"edge_{current_node_id}_to_transform",
                "source": current_node_id,
                "target": f"transform_{len(nodes)}",
                "type": "smoothstep",
                "animated": True
            })

            current_node_id = f"transform_{len(nodes)}"
            current_x += 200

        # Validation node
        if force_edi_validation or tweak_edi:
            validate_node = {
                "id": f"validate_{len(nodes)+1}",
                "type": "validate",
                "position": {"x": current_x, "y": 100},
                "data": {
                    "id": f"validate_{len(nodes)+1}",
                    "label": "Validation",
                    "rules": json.dumps([{
                        "type": "edi_validation" if force_edi_validation else "edi_tweak",
                        "enabled": True
                    }])
                }
            }
            nodes.append(validate_node)

            edges.append({
                "id": f"edge_{current_node_id}_to_validate",
                "source": current_node_id,
                "target": f"validate_{len(nodes)}",
                "type": "smoothstep",
                "animated": True
            })

            current_node_id = f"validate_{len(nodes)}"
            current_x += 200

        # Split EDI node
        if split_edi:
            router_node = {
                "id": f"router_{len(nodes)+1}",
                "type": "router",
                "position": {"x": current_x, "y": 100},
                "data": {
                    "id": f"router_{len(nodes)+1}",
                    "label": "Document Router",
                    "conditions": json.dumps([{
                        "type": "document_type",
                        "condition": "contains",
                        "value": "invoice"
                    }])
                }
            }
            nodes.append(router_node)

            edges.append({
                "id": f"edge_{current_node_id}_to_router",
                "source": current_node_id,
                "target": f"router_{len(nodes)}",
                "type": "smoothstep",
                "animated": True
            })

            current_node_id = f"router_{len(nodes)}"
            current_x += 200

        # Additional processing nodes based on legacy flags
        if append_a_records:
            text_node = {
                "id": f"text_{len(nodes)+1}",
                "type": "text",
                "position": {"x": current_x, "y": 100},
                "data": {
                    "id": f"text_{len(nodes)+1}",
                    "label": "Append Records",
                    "operation": "append",
                    "appendText": folder_row.get("a_record_append_text", "APPEND_TEXT")
                }
            }
            nodes.append(text_node)

            edges.append({
                "id": f"edge_{current_node_id}_to_text",
                "source": current_node_id,
                "target": f"text_{len(nodes)}",
                "type": "smoothstep",
                "animated": True
            })

            current_node_id = f"text_{len(nodes)}"
            current_x += 200

        if invoice_date_offset != 0:
            date_node = {
                "id": f"date_{len(nodes)+1}",
                "type": "date",
                "position": {"x": current_x, "y": 100},
                "data": {
                    "id": f"date_{len(nodes)+1}",
                    "label": "Date Offset",
                    "operation": "offset",
                    "offsetDays": invoice_date_offset
                }
            }
            nodes.append(date_node)

            edges.append({
                "id": f"edge_{current_node_id}_to_date",
                "source": current_node_id,
                "target": f"date_{len(nodes)}",
                "type": "smoothstep",
                "animated": True
            })

            current_node_id = f"date_{len(nodes)}"
            current_x += 200

        if force_each_upc or retail_uom != 0:
            transform_node = {
                "id": f"transform_unit_{len(nodes)+1}",
                "type": "transform",
                "position": {"x": current_x, "y": 100},
                "data": {
                    "id": f"transform_unit_{len(nodes)+1}",
                    "label": "Unit Conversion",
                    "transformations": json.dumps([{
                        "type": "unit_conversion",
                        "forceEachUpc": force_each_upc,
                        "retailUom": retail_uom
                    }])
                }
            }
            nodes.append(transform_node)

            edges.append({
                "id": f"edge_{current_node_id}_to_unit_transform",
                "source": current_node_id,
                "target": f"transform_unit_{len(nodes)}",
                "type": "smoothstep",
                "animated": True
            })

            current_node_id = f"transform_unit_{len(nodes)}"
            current_x += 200

        # Connect to output node
        edges.append({
            "id": f"edge_{current_node_id}_to_output",
            "source": current_node_id,
            "target": "output_destination_1",
            "type": "smoothstep",
            "animated": True
        })

        return pipeline_data

    except Exception as e:
        raise ValueError(f"Error parsing legacy config: {str(e)}")

def determine_file_pattern(folder_row: Dict[str, Any]) -> str:
    """
    Determine file pattern based on legacy configuration
    """
    convert_to_format = folder_row.get("convert_to_format", "")
    if convert_to_format:
        if convert_to_format.lower() == "csv":
            return "*.csv"
        elif convert_to_format.lower() == "edi":
            return "*.edi"
        else:
            return f"*.{convert_to_format.lower()}"
    else:
        # Default to EDI if processing EDI
        if folder_row.get("process_edi", "False") == "True":
            return "*.edi"
        else:
            return "*.*"

def determine_output_protocol(folder_row: Dict[str, Any]) -> str:
    """
    Determine output protocol based on legacy backend settings
    """
    # Check for various backend processing flags
    if folder_row.get("process_backend_copy", False):
        return "local"
    elif folder_row.get("process_backend_ftp", False):
        return "ftp"
    elif folder_row.get("process_backend_email", False):
        return "email"
    else:
        return "local"

def determine_output_config(folder_row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Determine output configuration based on legacy backend settings
    """
    output_config = {}

    # Handle different backend types
    if folder_row.get("process_backend_copy", False):
        output_config["path"] = folder_row.get("copy_to_directory", "")
    elif folder_row.get("process_backend_ftp", False):
        output_config.update({
            "host": folder_row.get("ftp_server", ""),
            "username": folder_row.get("ftp_username", ""),
            "password": folder_row.get("ftp_password", ""),
            "port": folder_row.get("ftp_port", 21),
            "remotePath": folder_row.get("ftp_folder", "/")
        })
    elif folder_row.get("process_backend_email", False):
        output_config.update({
            "to": folder_row.get("email_to", ""),
            "subject": folder_row.get("email_subject_line", "Processed File"),
            "smtpServer": folder_row.get("email_smtp_server", ""),
            "username": folder_row.get("email_username", ""),
            "password": folder_row.get("email_password", "")
        })

    return output_config

def import_legacy_database(file_path: str) -> ImportResult:
    """
    Import legacy folders.db and convert to pipelines
    """
    errors = []
    imported_count = 0
    
    try:
        # Connect to the legacy database
        conn = sqlite3.connect(file_path)
        cursor = conn.cursor()
        
        # Query all active folders
        cursor.execute("""
            SELECT * FROM folders 
            WHERE folder_is_active = "True" OR folder_is_active = 1
        """)
        
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        
        # Convert rows to dictionaries
        legacy_folders = []
        for row in rows:
            folder_dict = {}
            for i, col in enumerate(columns):
                folder_dict[col] = row[i]
            legacy_folders.append(folder_dict)
        
        conn.close()
        
        # Import each folder as a pipeline
        db = get_database()
        
        for folder in legacy_folders:
            try:
                # Convert legacy config to pipeline
                pipeline_data = parse_legacy_folder_config(folder)
                
                # Create pipeline in database
                from backend.api.pipelines import create_pipeline
                from backend.models.pipeline import PipelineCreate
                
                pipeline_create = PipelineCreate(**{
                    "name": pipeline_data["name"],
                    "description": pipeline_data["description"],
                    "nodes": pipeline_data["nodes"],
                    "edges": pipeline_data["edges"],
                    "is_active": pipeline_data.get("is_active", True)
                })
                
                # Use the existing create_pipeline function
                pipeline_result = create_pipeline(pipeline_create)
                imported_count += 1
                
            except Exception as e:
                errors.append(f"Error importing folder '{folder.get('alias', 'Unknown')}': {str(e)}")
        
        return ImportResult(
            success=len(errors) == 0,
            message=f"Successfully imported {imported_count} pipelines with {len(errors)} errors",
            imported_pipelines=imported_count,
            errors=errors
        )
        
    except Exception as e:
        errors.append(f"Database connection error: {str(e)}")
        return ImportResult(
            success=False,
            message=f"Failed to import database: {str(e)}",
            imported_pipelines=0,
            errors=errors
        )

@router.post("/import-db", response_model=ImportResult)
async def import_legacy_db(file: UploadFile = File(...)):
    """
    Import a legacy folders.db file and convert to pipelines
    """
    # Validate file type
    if not file.filename.endswith(".db"):
        raise HTTPException(status_code=400, detail="File must be a SQLite database (.db)")
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_file_path = tmp_file.name
    
    try:
        # Import the database
        result = import_legacy_database(tmp_file_path)
        return result
    finally:
        # Clean up temporary file
        os.unlink(tmp_file_path)

@router.post("/preview-db", response_model=List[PipelinePreview])
async def preview_legacy_import(file: UploadFile = File(...)):
    """
    Preview what pipelines would be created from a legacy database
    """
    # Validate file type
    if not file.filename.endswith(".db"):
        raise HTTPException(status_code=400, detail="File must be a SQLite database (.db)")
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_file_path = tmp_file.name
    
    previews = []
    
    try:
        # Connect to the legacy database
        conn = sqlite3.connect(tmp_file_path)
        cursor = conn.cursor()
        
        # Query all active folders
        cursor.execute("""
            SELECT * FROM folders 
            WHERE folder_is_active = "True" OR folder_is_active = 1
        """)
        
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        
        # Convert rows to dictionaries
        legacy_folders = []
        for row in rows:
            folder_dict = {}
            for i, col in enumerate(columns):
                folder_dict[col] = row[i]
            legacy_folders.append(folder_dict)
        
        conn.close()
        
        # Generate previews for each folder
        for i, folder in enumerate(legacy_folders):
            try:
                # Convert legacy config to pipeline to count nodes
                pipeline_data = parse_legacy_folder_config(folder)
                
                preview = PipelinePreview(
                    id=f"preview_{i+1}",
                    name=folder.get("alias", f"Pipeline {i+1}"),
                    description=f"Imported from legacy folder: {folder.get('folder_name', '')}",
                    node_count=len(pipeline_data.get("nodes", [])),
                    has_errors=False
                )
                
                previews.append(preview)
                
            except Exception as e:
                preview = PipelinePreview(
                    id=f"preview_{i+1}",
                    name=folder.get("alias", f"Pipeline {i+1}"),
                    description=f"Import error: {str(e)}",
                    node_count=0,
                    has_errors=True,
                    error_message=str(e)
                )
                
                previews.append(preview)
        
        return previews
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading database: {str(e)}")
    finally:
        # Clean up temporary file
        os.unlink(tmp_file_path)
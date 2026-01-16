import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Iterator
from dataclasses import dataclass, field
import hashlib
import logging
import tempfile
import os
from datetime import datetime, timedelta
import re
from functools import wraps
from time import sleep

from utils import do_split_edi, capture_records
from backend.remote_fs.factory import create_file_system


@dataclass
class PipelineNode:
    """Represents a node in the pipeline DAG"""

    id: str
    type: str
    label: str
    config: Dict[str, Any]
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    position: Dict[str, int] = field(default_factory=dict)


@dataclass
class PipelineContext:
    """Context passed through pipeline execution"""

    input_file: Path
    output_file: Path
    current_data: Optional[str] = None
    variables: Dict[str, Any] = field(default_factory=dict)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    node_outputs: Dict[str, Any] = field(default_factory=dict)
    node_execution_times: Dict[str, float] = field(default_factory=dict)
    node_attempts: Dict[str, int] = field(default_factory=dict)
    pipeline_metrics: Dict[str, Any] = field(default_factory=dict)
    canceled: bool = False

    def add_error(self, node_id: str, error: str, error_type: str = "error"):
        """Add an error to the context with detailed information"""
        self.errors.append({
            "node_id": node_id,
            "error": error,
            "error_type": error_type,
            "timestamp": datetime.now().isoformat()
        })

    def set_node_execution_time(self, node_id: str, execution_time: float):
        """Set execution time for a node"""
        self.node_execution_times[node_id] = execution_time

    def increment_node_attempts(self, node_id: str):
        """Increment the number of attempts for a node"""
        self.node_attempts[node_id] = self.node_attempts.get(node_id, 0) + 1

    def get_node_attempts(self, node_id: str) -> int:
        """Get the number of attempts for a node"""
        return self.node_attempts.get(node_id, 0)


logger = logging.getLogger(__name__)


def retry_with_backoff(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator to add retry logic with exponential backoff to functions.
    
    Args:
        max_retries: Maximum number of retries
        delay: Initial delay in seconds
        backoff: Multiplier for exponential backoff
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(f"Attempt {attempt + 1} failed: {e}")
                    
                    if attempt < max_retries:
                        sleep_delay = delay * (backoff ** attempt)
                        logger.info(f"Retrying in {sleep_delay:.2f} seconds...")
                        sleep(sleep_delay)
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed: {e}")
            
            if last_exception is not None:
                raise last_exception
            raise Exception("Function failed without raising an exception")
        return wrapper
    return decorator


class PipelineExecutor:
    """
    Executes pipeline DAGs to process EDI files.

    The executor:
    1. Loads and validates the pipeline JSON
    2. Topologically sorts nodes (DAG)
    3. Executes each node in order
    4. Produces converter-equivalent output
    """

    def __init__(self, pipeline_path: Path):
        self.pipeline_path = Path(pipeline_path)
        self.nodes: Dict[str, PipelineNode] = {}
        self.edges: List[Dict] = []
        self.context = None

    def load_pipeline(self) -> Dict:
        """Load pipeline from JSON file"""
        with open(self.pipeline_path, "r") as f:
            return json.load(f)

    def parse_pipeline(self, pipeline_data: Dict) -> List[PipelineNode]:
        """Parse pipeline JSON into node objects"""
        self.nodes = {}

        # Handle both React Flow format and simple format
        nodes_data = pipeline_data.get("nodes", [])
        edges_data = pipeline_data.get("edges", [])

        for node in nodes_data:
            node_obj = PipelineNode(
                id=node.get("id", ""),
                type=node.get("type", ""),
                label=node.get("data", {}).get("label", node.get("label", "")),
                config=node.get("data", {}),
                position=node.get("position", {}),
            )
            self.nodes[node_obj.id] = node_obj

        self.edges = edges_data
        return list(self.nodes.values())

    def validate_pipeline(self) -> List[Dict[str, Any]]:
        """Validate pipeline configuration and structure"""
        errors = []
        
        # Check for valid nodes
        if not self.nodes:
            errors.append({"error": "Pipeline contains no nodes", "error_type": "critical"})
        
        # Check for start node
        has_start_node = any(node.type == "start" for node in self.nodes.values())
        if not has_start_node:
            errors.append({"error": "Pipeline must contain a start node", "error_type": "critical"})
        
        # Check for end node
        has_end_node = any(node.type == "end" for node in self.nodes.values())
        if not has_end_node:
            errors.append({"error": "Pipeline must contain an end node", "error_type": "critical"})
        
        # Check for circular dependencies (using Kahn's algorithm)
        in_degree = {node_id: 0 for node_id in self.nodes}
        for edge in self.edges:
            target = edge.get("target")
            if target in in_degree:
                in_degree[target] += 1
        
        # Perform Kahn's algorithm to find cycles
        temp_in_degree = in_degree.copy()
        queue = [node_id for node_id in self.nodes if temp_in_degree[node_id] == 0]
        visited = []
        
        while queue:
            node_id = queue.pop(0)
            visited.append(node_id)
            
            for edge in self.edges:
                if edge.get("source") == node_id:
                    target = edge.get("target")
                    if target in temp_in_degree:
                        temp_in_degree[target] -= 1
                        if temp_in_degree[target] == 0:
                            queue.append(target)
        
        if len(visited) != len(self.nodes):
            errors.append({"error": "Pipeline contains circular dependencies", "error_type": "critical"})
        
        # Check for invalid node types
        valid_types = {
            "folderSource", "extract", "remapper", "transform", "filter", "router", 
            "join", "aggregate", "validate", "query", "profile", "output", "start", 
            "end", "trigger", "sort", "dedupe", "union", "pivot", "unpivot", "text", 
            "date", "impute", "normalize", "outlier", "lookupTable", "apiEnrich", 
            "delay", "cache", "readJson", "writeJson", "readExcel", "writeExcel"
        }
        
        for node_id, node in self.nodes.items():
            if node.type not in valid_types:
                errors.append({
                    "error": f"Invalid node type '{node.type}' for node '{node_id}'",
                    "error_type": "critical"
                })
        
        # Check for valid connections
        for edge in self.edges:
            source = edge.get("source")
            target = edge.get("target")
            
            if source not in self.nodes:
                errors.append({
                    "error": f"Edge from unknown source node '{source}'",
                    "error_type": "critical"
                })
            
            if target not in self.nodes:
                errors.append({
                    "error": f"Edge to unknown target node '{target}'",
                    "error_type": "critical"
                })
        
        return errors

    def get_execution_order(self) -> List[str]:
        """Get topologically sorted execution order using Kahn's algorithm (DAG)"""
        # Calculate in-degree for each node
        in_degree = {node_id: 0 for node_id in self.nodes}
        for edge in self.edges:
            target = edge.get("target")
            if target in in_degree:
                in_degree[target] += 1
        
        # Queue for nodes with no incoming edges (in-degree 0)
        queue = [node_id for node_id in self.nodes if in_degree[node_id] == 0]
        execution_order = []
        
        while queue:
            node_id = queue.pop(0)
            execution_order.append(node_id)
            
            # Reduce in-degree of all neighbors
            for edge in self.edges:
                if edge.get("source") == node_id:
                    target = edge.get("target")
                    if target in in_degree:
                        in_degree[target] -= 1
                        if in_degree[target] == 0:
                            queue.append(target)
        
        return execution_order

    def execute_node(self, node_id: str, context: PipelineContext) -> bool:
        """Execute a single node"""
        node = self.nodes[node_id]
        node_type = node.type

        # Map frontend node types to backend handlers
        type_mapping = {
            "folderSource": "_handle_input_source",
            "extract": "_handle_extract",
            "remapper": "_handle_remapper",
            "transform": "_handle_transform",
            "filter": "_handle_filter",
            "router": "_handle_router",
            "join": "_handle_join",
            "aggregate": "_handle_aggregate",
            "validate": "_handle_validate",
            "query": "_handle_query",
            "profile": "_handle_profile",
            "output": "_handle_output",
            "start": "_handle_start",
            "end": "_handle_end",
            "trigger": "_handle_trigger",
            "sort": "_handle_sort",
            "dedupe": "_handle_dedupe",
            "union": "_handle_union",
            "pivot": "_handle_pivot",
            "unpivot": "_handle_unpivot",
            "text": "_handle_text",
            "date": "_handle_date",
            "impute": "_handle_impute",
            "normalize": "_handle_normalize",
            "outlier": "_handle_outlier",
            "lookupTable": "_handle_lookup_table",
            "apiEnrich": "_handle_api_enrich",
            "delay": "_handle_delay",
            "cache": "_handle_cache",
            "readJson": "_handle_read_json",
            "writeJson": "_handle_write_json",
            "readExcel": "_handle_read_excel",
            "writeExcel": "_handle_write_excel",
        }

        handler_name = type_mapping.get(node_type)
        if handler_name:
            handler = getattr(self, handler_name)
            return handler(node, context)
        else:
            logger.error(f"Unknown node type: {node_type}")
            context.add_error(node_id, f"Unknown node type: {node_type}", "error")
            return False

    # Node handlers - these implement converter logic
    def _handle_start(self, node: PipelineNode, context: PipelineContext) -> bool:
        """Start node - initializes pipeline"""
        context.variables["start_time"] = datetime.now()
        return True

    def _handle_end(self, node: PipelineNode, context: PipelineContext) -> bool:
        """End node - finalizes pipeline"""
        return True

    def _handle_trigger(self, node: PipelineNode, context: PipelineContext) -> bool:
        """Trigger node - checks trigger conditions"""
        config = node.config
        trigger_type = config.get("triggerType", "manual")
        # Implement trigger logic
        return True

    @retry_with_backoff(max_retries=3, delay=1.0, backoff=2.0)
    def _handle_input_source(
        self, node: PipelineNode, context: PipelineContext
    ) -> bool:
        """Input source node - reads input file with enhanced remote file system support"""
        try:
            config = node.config
            source_type = config.get('source_type', 'local')
            source_path = config.get('path', '')

            params = {}
            if source_type == "local":
                params = {"base_path": config.get("base_dir", "")}
            elif source_type == "smb":
                params = {
                    "host": config.get("host"),
                    "username": config.get("username"),
                    "password": config.get("password"),
                    "share": config.get("share", ""),
                    "port": config.get("port", 445),
                }
            elif source_type == "sftp":
                params = {
                    "host": config.get("host"),
                    "username": config.get("username"),
                    "password": config.get("password"),
                    "private_key_path": config.get("private_key_path", ""),
                    "port": config.get("port", 22),
                }
            elif source_type == "ftp":
                params = {
                    "host": config.get("host"),
                    "username": config.get("username"),
                    "password": config.get("password"),
                    "port": config.get("port", 21),
                    "use_tls": config.get("use_tls", True),
                }

            file_system = create_file_system(source_type, params)

            # Check if file exists before downloading
            if not file_system.file_exists(source_path):
                raise Exception(f"File not found: {source_path}")

            # Download file to temporary location
            temp_dir = tempfile.mkdtemp()
            local_path = os.path.join(temp_dir, os.path.basename(source_path))

            if not file_system.download_file(source_path, local_path):
                raise Exception(f"Failed to download file from {source_path}")

            logger.debug(f"Successfully downloaded file to: {local_path}")

            # Process the file
            with open(local_path, 'r') as edi_file:
                data = edi_file.read()
                documents = do_split_edi(data, temp_dir, params)
                transactions = capture_records(documents)

            logger.debug(f"Processed {len(transactions)} transactions from file")
            context.node_outputs[node.id] = transactions
            return True
        except Exception as e:
            logger.error(f"Input source error (node {node.id}): {e}")
            context.add_error(node.id, str(e), "error")
            return False

    @retry_with_backoff(max_retries=3, delay=1.0, backoff=2.0)
    def _handle_output(self, node: PipelineNode, context: PipelineContext) -> bool:
        """Output node - writes output file with enhanced remote file system support"""
        config = node.config
        protocol = config.get("protocol", "local")

        # Get input data from upstream nodes
        output_content = self._get_input_data(node, context)

        try:
            if protocol == "local":
                output_path = config.get("path", context.output_file)
                with open(output_path, "w") as f:
                    f.write(output_content)
                logger.debug(f"Successfully wrote output to local file: {output_path}")
            else:
                # Handle remote file systems
                remote_path = config.get("path", "")
                if not remote_path:
                    raise Exception("Output path is required for remote protocols")

                params = {}
                if protocol == "smb":
                    params = {
                        "host": config.get("host"),
                        "username": config.get("username"),
                        "password": config.get("password"),
                        "share": config.get("share", ""),
                        "port": config.get("port", 445),
                    }
                elif protocol == "sftp":
                    params = {
                        "host": config.get("host"),
                        "username": config.get("username"),
                        "password": config.get("password"),
                        "private_key_path": config.get("private_key_path", ""),
                        "port": config.get("port", 22),
                    }
                elif protocol == "ftp":
                    params = {
                        "host": config.get("host"),
                        "username": config.get("username"),
                        "password": config.get("password"),
                        "port": config.get("port", 21),
                        "use_tls": config.get("use_tls", True),
                    }

                file_system = create_file_system(protocol, params)

                # Write to temporary file first
                temp_dir = tempfile.mkdtemp()
                temp_path = os.path.join(temp_dir, "temp_output.txt")
                with open(temp_path, "w") as f:
                    f.write(output_content)

                # Upload to remote system
                if not file_system.upload_file(temp_path, remote_path):
                    raise Exception(f"Failed to upload file to {remote_path}")

                logger.debug(f"Successfully uploaded output to remote path: {remote_path}")

            return True
        except Exception as e:
            logger.error(f"Output error (node {node.id}): {e}")
            context.add_error(node.id, str(e), "error")
            return False

    def _handle_router(self, node: PipelineNode, context: PipelineContext) -> bool:
        """Router node - routes data TRUE/FALSE based on condition"""
        config = node.config
        conditions = json.loads(config.get("conditions", "[]"))
        logic = config.get("logic", "AND")

        # Get input data from upstream nodes
        input_data = self._get_input_data(node, context)

        # Apply routing logic
        if isinstance(input_data, list):
            true_branch = []
            false_branch = []

            for record in input_data:
                matches = True
                for condition in conditions:
                    field = condition.get("field", "")
                    operator = condition.get("operator", "equals")
                    value = condition.get("value", "")

                    record_value = record.get(field, "")

                    if operator == "equals":
                        match = record_value == value
                    elif operator == "not_equals":
                        match = record_value != value
                    elif operator == "greater":
                        match = record_value > value
                    elif operator == "less":
                        match = record_value < value
                    elif operator == "contains":
                        match = value in str(record_value)
                    elif operator == "is_null":
                        match = record_value is None or record_value == ""
                    elif operator == "is_not_null":
                        match = record_value is not None and record_value != ""
                    else:
                        match = False

                    if logic == "AND" and not match:
                        matches = False
                        break
                    elif logic == "OR" and match:
                        matches = True
                        break

                if matches:
                    true_branch.append(record)
                else:
                    false_branch.append(record)

            # Store outputs for downstream nodes
            context.node_outputs[f"{node.id}_true"] = true_branch
            context.node_outputs[f"{node.id}_false"] = false_branch
        else:
            # Handle single data item
            matches = True
            for condition in conditions:
                field = condition.get("field", "")
                operator = condition.get("operator", "equals")
                value = condition.get("value", "")

                if operator == "equals":
                    match = input_data.get(field, "") == value
                elif operator == "not_equals":
                    match = input_data.get(field, "") != value
                elif operator == "greater":
                    match = input_data.get(field, "") > value
                elif operator == "less":
                    match = input_data.get(field, "") < value
                elif operator == "contains":
                    match = value in str(input_data.get(field, ""))
                elif operator == "is_null":
                    match = input_data.get(field, "") is None or input_data.get(field, "") == ""
                elif operator == "is_not_null":
                    match = input_data.get(field, "") is not None and input_data.get(field, "") != ""
                else:
                    match = False

                if logic == "AND" and not match:
                    matches = False
                    break
                elif logic == "OR" and match:
                    matches = True
                    break

            if matches:
                context.node_outputs[f"{node.id}_true"] = input_data
            else:
                context.node_outputs[f"{node.id}_false"] = input_data

        return True

    def _handle_remapper(self, node: PipelineNode, context: PipelineContext) -> bool:
        """Remapper node - remaps field names"""
        config = node.config
        mappings_str = config.get("mappings", "[]")
        drop_others = config.get("dropOthers", True)

        try:
            mappings = json.loads(mappings_str)
        except json.JSONDecodeError:
            mappings = []

        # Get input data from upstream nodes
        input_data = self._get_input_data(node, context)

        if isinstance(input_data, list):
            # Process list of records
            output_data = []
            for record in input_data:
                new_record = {}
                for mapping in mappings:
                    source_field = mapping.get("source", "")
                    target_field = mapping.get("target", "")
                    transform = mapping.get("transform", "none")

                    if source_field in record:
                        value = record[source_field]

                        # Apply transformation
                        if transform == "upper":
                            value = str(value).upper()
                        elif transform == "lower":
                            value = str(value).lower()
                        elif transform == "title":
                            value = str(value).title()
                        elif transform == "trim":
                            value = str(value).strip()
                        elif transform == "number":
                            try:
                                value = float(value)
                            except ValueError:
                                value = value

                        new_record[target_field] = value

                if not drop_others:
                    # Keep original fields not in mappings
                    for key, value in record.items():
                        if key not in [m.get("source", "") for m in mappings]:
                            new_record[key] = value

                output_data.append(new_record)
        else:
            # Process single record
            output_data = {}
            for mapping in mappings:
                source_field = mapping.get("source", "")
                target_field = mapping.get("target", "")
                transform = mapping.get("transform", "none")

                if isinstance(input_data, dict) and source_field in input_data:
                    value = input_data[source_field]

                    # Apply transformation
                    if transform == "upper":
                        value = str(value).upper()
                    elif transform == "lower":
                        value = str(value).lower()
                    elif transform == "title":
                        value = str(value).title()
                    elif transform == "trim":
                        value = str(value).strip()
                    elif transform == "number":
                        try:
                            value = float(value)
                        except ValueError:
                            value = value

                    output_data[target_field] = value

            if not drop_others and isinstance(input_data, dict):
                # Keep original fields not in mappings
                for key, value in input_data.items():
                    if key not in [m.get("source", "") for m in mappings]:
                        output_data[key] = value

        context.node_outputs[node.id] = output_data
        return True

    def _handle_extract(self, node: PipelineNode, context: PipelineContext) -> bool:
        """Extract node - extracts specific fields from data"""
        config = node.config
        field_mappings_str = config.get("fieldMappings", "[]")

        try:
            field_mappings = json.loads(field_mappings_str)
        except json.JSONDecodeError:
            field_mappings = []

        # Get input data from upstream nodes
        input_data = self._get_input_data(node, context)

        if isinstance(input_data, list):
            # Process list of records
            output_data = []
            for record in input_data:
                new_record = {}
                for mapping in field_mappings:
                    source = mapping.get("source", "")
                    target = mapping.get("target", "")
                    transform = mapping.get("transform", "none")

                    if source in record:
                        value = record[source]

                        # Apply transformation
                        if transform == "upper":
                            value = str(value).upper()
                        elif transform == "lower":
                            value = str(value).lower()
                        elif transform == "title":
                            value = str(value).title()
                        elif transform == "trim":
                            value = str(value).strip()
                        elif transform == "number":
                            try:
                                value = float(value)
                            except ValueError:
                                value = value

                        new_record[target] = value
                output_data.append(new_record)
        else:
            # Process single record
            output_data = {}
            if isinstance(input_data, dict):
                for mapping in field_mappings:
                    source = mapping.get("source", "")
                    target = mapping.get("target", "")
                    transform = mapping.get("transform", "none")

                    if source in input_data:
                        value = input_data[source]

                        # Apply transformation
                        if transform == "upper":
                            value = str(value).upper()
                        elif transform == "lower":
                            value = str(value).lower()
                        elif transform == "title":
                            value = str(value).title()
                        elif transform == "trim":
                            value = str(value).strip()
                        elif transform == "number":
                            try:
                                value = float(value)
                            except ValueError:
                                value = value

                        output_data[target] = value

        context.node_outputs[node.id] = output_data
        return True

    def _handle_transform(self, node: PipelineNode, context: PipelineContext) -> bool:
        """Transform node - performs calculations and transformations"""
        config = node.config
        transformations_str = config.get("transformations", "[]")

        try:
            transformations = json.loads(transformations_str)
        except json.JSONDecodeError:
            transformations = []

        # Get input data from upstream nodes
        input_data = self._get_input_data(node, context)

        if isinstance(input_data, list):
            # Process list of records
            output_data = []
            for record in input_data:
                new_record = record.copy()  # Start with original data
                for transform in transformations:
                    field = transform.get("field", "")
                    expression = transform.get("expression", "")
                    alias = transform.get("alias", "")

                    # Evaluate expression using Python eval (be careful!)
                    # In a production system, use a safer evaluation method
                    try:
                        # Prepare local variables from the record
                        local_vars = record.copy()
                        result = eval(expression, {"__builtins__": {}}, local_vars)

                        # Store result in the specified field or alias
                        target_field = alias if alias else field
                        new_record[target_field] = result
                    except Exception as e:
                        logger.error(f"Transform error: {e}")
                        context.errors.append(f"Transform error: {e}")

                output_data.append(new_record)
        else:
            # Process single record
            output_data = input_data.copy() if isinstance(input_data, dict) else {}
            for transform in transformations:
                field = transform.get("field", "")
                expression = transform.get("expression", "")
                alias = transform.get("alias", "")

                # Evaluate expression using Python eval (be careful!)
                # In a production system, use a safer evaluation method
                try:
                    # Prepare local variables from the record
                    local_vars = input_data.copy() if isinstance(input_data, dict) else {}
                    result = eval(expression, {"__builtins__": {}}, local_vars)

                    # Store result in the specified field or alias
                    target_field = alias if alias else field
                    output_data[target_field] = result
                except Exception as e:
                    logger.error(f"Transform error: {e}")
                    context.errors.append(f"Transform error: {e}")

        context.node_outputs[node.id] = output_data
        return True

    def _handle_filter(self, node: PipelineNode, context: PipelineContext) -> bool:
        """Filter node - filters rows based on condition"""
        config = node.config
        conditions_str = config.get("conditions", "[]")
        logic = config.get("logic", "AND")

        try:
            conditions = json.loads(conditions_str)
        except json.JSONDecodeError:
            conditions = []

        # Get input data from upstream nodes
        input_data = self._get_input_data(node, context)

        if isinstance(input_data, list):
            # Process list of records
            filtered_data = []
            for record in input_data:
                matches = True
                for condition in conditions:
                    field = condition.get("field", "")
                    operator = condition.get("operator", "equals")
                    value = condition.get("value", "")

                    record_value = record.get(field, "")

                    if operator == "equals":
                        match = record_value == value
                    elif operator == "not_equals":
                        match = record_value != value
                    elif operator == "greater":
                        match = record_value > value
                    elif operator == "less":
                        match = record_value < value
                    elif operator == "contains":
                        match = value in str(record_value)
                    elif operator == "is_null":
                        match = record_value is None or record_value == ""
                    elif operator == "is_not_null":
                        match = record_value is not None and record_value != ""
                    else:
                        match = False

                    if logic == "AND" and not match:
                        matches = False
                        break
                    elif logic == "OR" and match:
                        matches = True
                        break

                if matches:
                    filtered_data.append(record)
        else:
            # Handle single data item
            matches = True
            for condition in conditions:
                field = condition.get("field", "")
                operator = condition.get("operator", "equals")
                value = condition.get("value", "")

                if operator == "equals":
                    match = input_data.get(field, "") == value
                elif operator == "not_equals":
                    match = input_data.get(field, "") != value
                elif operator == "greater":
                    match = input_data.get(field, "") > value
                elif operator == "less":
                    match = input_data.get(field, "") < value
                elif operator == "contains":
                    match = value in str(input_data.get(field, ""))
                elif operator == "is_null":
                    match = input_data.get(field, "") is None or input_data.get(field, "") == ""
                elif operator == "is_not_null":
                    match = input_data.get(field, "") is not None and input_data.get(field, "") != ""
                else:
                    match = False

                if logic == "AND" and not match:
                    matches = False
                    break
                elif logic == "OR" and match:
                    matches = True
                    break

            filtered_data = input_data if matches else {}

        context.node_outputs[node.id] = filtered_data
        return True

    def _handle_sort(self, node: PipelineNode, context: PipelineContext) -> bool:
        """Sort node - sorts data"""
        config = node.config
        sort_fields_str = config.get("sortFields", "[]")

        try:
            sort_fields = json.loads(sort_fields_str)
        except json.JSONDecodeError:
            sort_fields = []

        # Get input data from upstream nodes
        input_data = self._get_input_data(node, context)

        if isinstance(input_data, list):
            # Sort list of records
            def sort_key(record):
                key_values = []
                for sort_field in sort_fields:
                    field = sort_field.get("field", "")
                    direction = sort_field.get("direction", "asc")

                    value = record.get(field, "")
                    if direction.lower() == "desc":
                        # For descending, we negate the value (for numeric) or reverse comparison
                        if isinstance(value, (int, float)):
                            value = -value
                        else:
                            # For strings, we'll handle in the sort function
                            value = (0, str(value)) if direction.lower() == "desc" else (1, str(value))

                    key_values.append(value)
                return tuple(key_values)

            # For mixed types, we need a more sophisticated approach
            def safe_sort_key(record):
                key_values = []
                for sort_field in sort_fields:
                    field = sort_field.get("field", "")
                    direction = sort_field.get("direction", "asc")

                    value = record.get(field, "")

                    # Convert to comparable format
                    if isinstance(value, (int, float)):
                        sort_val = value
                    elif isinstance(value, str):
                        sort_val = value.lower()
                    else:
                        sort_val = str(value).lower()

                    if direction.lower() == "desc":
                        # For descending sort, we use a tuple that inverts the comparison
                        key_values.append((1, sort_val))  # Higher priority for desc
                    else:
                        key_values.append((0, sort_val))  # Lower priority for asc

                return tuple(key_values)

            try:
                sorted_data = sorted(input_data, key=safe_sort_key)
            except TypeError:
                # If sorting fails due to incompatible types, return original data
                sorted_data = input_data
        else:
            # Single item doesn't need sorting
            sorted_data = input_data

        context.node_outputs[node.id] = sorted_data
        return True

    def _handle_dedupe(self, node: PipelineNode, context: PipelineContext) -> bool:
        """Dedupe node - removes duplicate records."""
        config = node.config
        dedupe_fields_str = config.get("dedupeFields", "[]")
        keep_strategy = config.get("keep", "first")

        try:
            dedupe_fields = json.loads(dedupe_fields_str)
        except json.JSONDecodeError:
            dedupe_fields = []

        # Get input data from upstream nodes
        input_data = self._get_input_data(node, context)

        if isinstance(input_data, list):
            seen_keys = set()
            deduped_data = []

            for record in input_data:
                # Create a key based on the dedupe fields
                key_parts = []
                for field in dedupe_fields:
                    key_parts.append(str(record.get(field, "")))

                key = "|".join(key_parts)

                if key not in seen_keys:
                    seen_keys.add(key)
                    deduped_data.append(record)
                elif keep_strategy == "last":
                    # If keeping last, replace the first occurrence
                    for i, existing_record in enumerate(deduped_data):
                        existing_key_parts = []
                        for field in dedupe_fields:
                            existing_key_parts.append(str(existing_record.get(field, "")))
                        existing_key = "|".join(existing_key_parts)

                        if existing_key == key:
                            deduped_data[i] = record
                            break
        else:
            # Single item doesn't need deduplication
            deduped_data = input_data

        context.node_outputs[node.id] = deduped_data
        return True

    def _handle_union(self, node: PipelineNode, context: PipelineContext) -> bool:
        """Union node - combines multiple inputs"""
        config = node.config
        sources_str = config.get("sources", "[]")

        try:
            sources = json.loads(sources_str)
        except json.JSONDecodeError:
            sources = []

        # Get input data from all upstream nodes
        all_data = []

        # Look for data from connected upstream nodes
        for edge in self.edges:
            if edge.get("target") == node.id:
                source_node_id = edge.get("source")
                if source_node_id and source_node_id in context.node_outputs:
                    source_data = context.node_outputs[source_node_id]
                    if isinstance(source_data, list):
                        all_data.extend(source_data)
                    elif source_data:  # Single item
                        all_data.append(source_data)

        context.node_outputs[node.id] = all_data
        return True

    def _handle_join(self, node: PipelineNode, context: PipelineContext) -> bool:
        """Join node - SQL-style join"""
        config = node.config
        join_type = config.get("joinType", "inner")
        join_keys_str = config.get("joinKeys", "[]")
        output_fields_str = config.get("outputFields", "[]")
        prefix_tables = config.get("prefixTables", True)

        try:
            join_keys = json.loads(join_keys_str)
            output_fields = json.loads(output_fields_str)
        except json.JSONDecodeError:
            join_keys = []
            output_fields = []

        # Find connected input nodes
        left_data = []
        right_data = []

        # This is a simplified implementation - in a real system, we'd need to identify
        # which upstream nodes are the left and right sides of the join
        upstream_nodes = self._get_upstream_nodes(node.id)
        if len(upstream_nodes) >= 2:
            # Take the first two upstream nodes as left and right
            left_node_id = upstream_nodes[0]
            right_node_id = upstream_nodes[1]

            if left_node_id in context.node_outputs:
                left_data = context.node_outputs[left_node_id]
                if not isinstance(left_data, list):
                    left_data = [left_data] if left_data else []

            if right_node_id in context.node_outputs:
                right_data = context.node_outputs[right_node_id]
                if not isinstance(right_data, list):
                    right_data = [right_data] if right_data else []

        # Perform the join
        joined_data = []

        if join_type == "inner":
            for left_record in left_data:
                for right_record in right_data:
                    # Check if join keys match
                    match = True
                    for key_pair in join_keys:
                        left_key = key_pair.get("left", "")
                        right_key = key_pair.get("right", "")

                        left_val = left_record.get(left_key)
                        right_val = right_record.get(right_key)

                        if left_val != right_val:
                            match = False
                            break

                    if match:
                        # Combine records
                        joined_record = {}

                        # Add left side fields
                        for key, value in left_record.items():
                            field_name = f"LEFT_{key}" if prefix_tables else key
                            joined_record[field_name] = value

                        # Add right side fields
                        for key, value in right_record.items():
                            field_name = f"RIGHT_{key}" if prefix_tables else key
                            joined_record[field_name] = value

                        joined_data.append(joined_record)

        elif join_type == "left":
            for left_record in left_data:
                matched = False
                for right_record in right_data:
                    # Check if join keys match
                    match = True
                    for key_pair in join_keys:
                        left_key = key_pair.get("left", "")
                        right_key = key_pair.get("right", "")

                        left_val = left_record.get(left_key)
                        right_val = right_record.get(right_key)

                        if left_val != right_val:
                            match = False
                            break

                    if match:
                        matched = True
                        # Combine records
                        joined_record = {}

                        # Add left side fields
                        for key, value in left_record.items():
                            field_name = f"LEFT_{key}" if prefix_tables else key
                            joined_record[field_name] = value

                        # Add right side fields
                        for key, value in right_record.items():
                            field_name = f"RIGHT_{key}" if prefix_tables else key
                            joined_record[field_name] = value

                        joined_data.append(joined_record)

                if not matched:
                    # Add left record with nulls for right side
                    joined_record = {}

                    # Add left side fields
                    for key, value in left_record.items():
                        field_name = f"LEFT_{key}" if prefix_tables else key
                        joined_record[field_name] = value

                    # Add nulls for right side fields
                    if right_data:
                        sample_right = right_data[0] if right_data else {}
                        for key in sample_right.keys():
                            field_name = f"RIGHT_{key}" if prefix_tables else key
                            joined_record[field_name] = None

                    joined_data.append(joined_record)

        context.node_outputs[node.id] = joined_data
        return True

    def _handle_aggregate(self, node: PipelineNode, context: PipelineContext) -> bool:
        """Aggregate node - performs aggregation"""
        config = node.config
        group_by_str = config.get("groupFields", "[]")
        aggregations_str = config.get("aggregations", "[]")

        try:
            group_by = json.loads(group_by_str)
            aggregations = json.loads(aggregations_str)
        except json.JSONDecodeError:
            group_by = []
            aggregations = []

        # Get input data from upstream nodes
        input_data = self._get_input_data(node, context)

        if isinstance(input_data, list) and input_data:
            # Group the data
            grouped = {}
            for record in input_data:
                # Create group key
                key_parts = []
                for field in group_by:
                    key_parts.append(str(record.get(field, "")))
                key = "|".join(key_parts)

                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(record)

            # Perform aggregations for each group
            aggregated_data = []
            for group_key, group_records in grouped.items():
                result_record = {}

                # Add grouping fields
                key_parts = group_key.split("|")
                for i, field in enumerate(group_by):
                    result_record[field] = key_parts[i] if i < len(key_parts) else ""

                # Perform aggregations
                for agg in aggregations:
                    field = agg.get("field", "")
                    func = agg.get("function", "SUM").upper()
                    alias = agg.get("alias", f"{func}_{field}")

                    values = [r.get(field) for r in group_records if r.get(field) is not None]

                    if not values:
                        result = None
                    elif func == "SUM":
                        result = sum(v for v in values if isinstance(v, (int, float)))
                    elif func == "AVG":
                        numeric_vals = [v for v in values if isinstance(v, (int, float))]
                        result = sum(numeric_vals) / len(numeric_vals) if numeric_vals else 0
                    elif func == "COUNT":
                        result = len(values)
                    elif func == "MIN":
                        result = min(v for v in values if isinstance(v, (int, float))) if values else None
                    elif func == "MAX":
                        result = max(v for v in values if isinstance(v, (int, float))) if values else None
                    else:
                        result = values[0] if values else None

                    result_record[alias] = result

                aggregated_data.append(result_record)
        else:
            # Single item or empty list - return as is
            aggregated_data = input_data

        context.node_outputs[node.id] = aggregated_data
        return True

    def _handle_validate(self, node: PipelineNode, context: PipelineContext) -> bool:
        """Validate node - validates data"""
        config = node.config
        rules_str = config.get("rules", "[]")

        try:
            rules = json.loads(rules_str)
        except json.JSONDecodeError:
            rules = []

        # Get input data from upstream nodes
        input_data = self._get_input_data(node, context)

        validation_errors = []

        if isinstance(input_data, list):
            # Validate list of records
            for i, record in enumerate(input_data):
                for rule in rules:
                    field = rule.get("field", "")
                    rule_type = rule.get("type", "required")
                    message = rule.get("message", f"Validation failed for {field}")

                    value = record.get(field)

                    if rule_type == "required" and (value is None or value == ""):
                        validation_errors.append(f"Record {i}: {message}")
                    elif rule_type == "email" and value and not re.match(r"[^@]+@[^@]+\.[^@]+", str(value)):
                        validation_errors.append(f"Record {i}: {message}")
                    elif rule_type == "numeric" and value is not None and value != "":
                        try:
                            float(value)
                        except ValueError:
                            validation_errors.append(f"Record {i}: {message}")
                    elif rule_type == "date" and value:
                        # Basic date validation
                        try:
                            datetime.fromisoformat(str(value).replace('Z', '+00:00'))
                        except ValueError:
                            validation_errors.append(f"Record {i}: {message}")
                    elif rule_type == "pattern" and value:
                        pattern = rule.get("pattern", "")
                        if pattern and not re.match(pattern, str(value)):
                            validation_errors.append(f"Record {i}: {message}")
                    elif rule_type == "range" and value is not None and value != "":
                        try:
                            num_val = float(value)
                            min_val = rule.get("min")
                            max_val = rule.get("max")

                            if min_val is not None and num_val < min_val:
                                validation_errors.append(f"Record {i}: {message}")
                            if max_val is not None and num_val > max_val:
                                validation_errors.append(f"Record {i}: {message}")
                        except ValueError:
                            validation_errors.append(f"Record {i}: {message}")

        else:
            # Validate single record
            if isinstance(input_data, dict):
                for rule in rules:
                    field = rule.get("field", "")
                    rule_type = rule.get("type", "required")
                    message = rule.get("message", f"Validation failed for {field}")

                    value = input_data.get(field)

                    if rule_type == "required" and (value is None or value == ""):
                        validation_errors.append(message)
                    elif rule_type == "email" and value and not re.match(r"[^@]+@[^@]+\.[^@]+", str(value)):
                        validation_errors.append(message)
                    elif rule_type == "numeric" and value is not None and value != "":
                        try:
                            float(value)
                        except ValueError:
                            validation_errors.append(message)
                    elif rule_type == "date" and value:
                        # Basic date validation
                        try:
                            datetime.fromisoformat(str(value).replace('Z', '+00:00'))
                        except ValueError:
                            validation_errors.append(message)
                    elif rule_type == "pattern" and value:
                        pattern = rule.get("pattern", "")
                        if pattern and not re.match(pattern, str(value)):
                            validation_errors.append(message)
                    elif rule_type == "range" and value is not None and value != "":
                        try:
                            num_val = float(value)
                            min_val = rule.get("min")
                            max_val = rule.get("max")

                            if min_val is not None and num_val < min_val:
                                validation_errors.append(message)
                            if max_val is not None and num_val > max_val:
                                validation_errors.append(message)
                        except ValueError:
                            validation_errors.append(message)

        if validation_errors:
            context.errors.extend(validation_errors)
            # Depending on error handling strategy, we might return False here
            # For now, we'll continue processing but log the errors
            return True
        else:
            return True

    def _handle_text(self, node: PipelineNode, context: PipelineContext) -> bool:
        """Text node - performs text operations"""
        config = node.config
        operation = config.get("operation", "replace")

        # Get input data from upstream nodes
        input_data = self._get_input_data(node, context)

        if isinstance(input_data, list):
            # Process list of records
            output_data = []
            for record in input_data:
                if isinstance(record, dict):
                    new_record = {}
                    for key, value in record.items():
                        if isinstance(value, str):
                            if operation == "replace":
                                pattern = config.get("pattern", "")
                                replacement = config.get("replacement", "")
                                new_value = re.sub(pattern, replacement, value)
                            elif operation == "upper":
                                new_value = value.upper()
                            elif operation == "lower":
                                new_value = value.lower()
                            elif operation == "trim":
                                new_value = value.strip()
                            elif operation == "substring":
                                start = config.get("start", 0)
                                length = config.get("length", len(value))
                                new_value = value[start:start+length]
                            else:
                                new_value = value
                        else:
                            new_value = value
                        new_record[key] = new_value
                    output_data.append(new_record)
                else:
                    output_data.append(record)
        else:
            # Process single record
            if isinstance(input_data, dict):
                output_data = {}
                for key, value in input_data.items():
                    if isinstance(value, str):
                        if operation == "replace":
                            pattern = config.get("pattern", "")
                            replacement = config.get("replacement", "")
                            new_value = re.sub(pattern, replacement, value)
                        elif operation == "upper":
                            new_value = value.upper()
                        elif operation == "lower":
                            new_value = value.lower()
                        elif operation == "trim":
                            new_value = value.strip()
                        elif operation == "substring":
                            start = config.get("start", 0)
                            length = config.get("length", len(value))
                            new_value = value[start:start+length]
                        else:
                            new_value = value
                    else:
                        new_value = value
                    output_data[key] = new_value
            else:
                output_data = input_data

        context.node_outputs[node.id] = output_data
        return True

    def _handle_date(self, node: PipelineNode, context: PipelineContext) -> bool:
        """Date node - performs date operations"""
        config = node.config
        operation = config.get("operation", "parse")

        # Get input data from upstream nodes
        input_data = self._get_input_data(node, context)

        if isinstance(input_data, list):
            # Process list of records
            output_data = []
            for record in input_data:
                if isinstance(record, dict):
                    new_record = {}
                    for key, value in record.items():
                        if isinstance(value, str):
                            try:
                                if operation == "parse":
                                    # Parse date string to datetime object
                                    date_format = config.get("format", "%Y-%m-%d")
                                    parsed_date = datetime.strptime(value, date_format)
                                    new_value = parsed_date.isoformat()
                                elif operation == "format":
                                    # Format date to specific format
                                    input_format = config.get("inputFormat", "%Y-%m-%d")
                                    output_format = config.get("outputFormat", "%Y-%m-%d")
                                    parsed_date = datetime.strptime(value, input_format)
                                    new_value = parsed_date.strftime(output_format)
                                elif operation == "add_days":
                                    days = config.get("days", 0)
                                    date_format = config.get("format", "%Y-%m-%d")
                                    parsed_date = datetime.strptime(value, date_format)
                                    new_date = parsed_date + timedelta(days=days)
                                    new_value = new_date.strftime(date_format)
                                else:
                                    new_value = value
                            except ValueError:
                                # If parsing fails, keep original value
                                new_value = value
                        else:
                            new_value = value
                        new_record[key] = new_value
                    output_data.append(new_record)
                else:
                    output_data.append(record)
        else:
            # Process single record
            if isinstance(input_data, dict):
                output_data = {}
                for key, value in input_data.items():
                    if isinstance(value, str):
                        try:
                            if operation == "parse":
                                # Parse date string to datetime object
                                date_format = config.get("format", "%Y-%m-%d")
                                parsed_date = datetime.strptime(value, date_format)
                                new_value = parsed_date.isoformat()
                            elif operation == "format":
                                # Format date to specific format
                                input_format = config.get("inputFormat", "%Y-%m-%d")
                                output_format = config.get("outputFormat", "%Y-%m-%d")
                                parsed_date = datetime.strptime(value, input_format)
                                new_value = parsed_date.strftime(output_format)
                            elif operation == "add_days":
                                from datetime import timedelta
                                days = config.get("days", 0)
                                date_format = config.get("format", "%Y-%m-%d")
                                parsed_date = datetime.strptime(value, date_format)
                                new_date = parsed_date + timedelta(days=days)
                                new_value = new_date.strftime(date_format)
                            else:
                                new_value = value
                        except ValueError:
                            # If parsing fails, keep original value
                            new_value = value
                    else:
                        new_value = value
                    output_data[key] = new_value
            else:
                output_data = input_data

        context.node_outputs[node.id] = output_data
        return True

    def _handle_impute(self, node: PipelineNode, context: PipelineContext) -> bool:
        """Impute node - fills missing values"""
        config = node.config
        impute_fields_str = config.get("imputeFields", "[]")
        method = config.get("method", "fixed")

        try:
            impute_fields = json.loads(impute_fields_str)
        except json.JSONDecodeError:
            impute_fields = []

        # Get input data from upstream nodes
        input_data = self._get_input_data(node, context)

        if isinstance(input_data, list):
            # Process list of records
            output_data = []
            for record in input_data:
                if isinstance(record, dict):
                    new_record = record.copy()
                    for field in impute_fields:
                        field_name = field.get("field", "")
                        if field_name in new_record and (new_record[field_name] is None or new_record[field_name] == ""):
                            if method == "fixed":
                                new_record[field_name] = field.get("value", "")
                            elif method == "mean":
                                # Calculate mean of this field across all records
                                values = [r.get(field_name) for r in input_data if r.get(field_name) is not None and r.get(field_name) != ""]
                                numeric_vals = [v for v in values if isinstance(v, (int, float))]
                                if numeric_vals:
                                    new_record[field_name] = sum(numeric_vals) / len(numeric_vals)
                                else:
                                    new_record[field_name] = field.get("value", "")
                            elif method == "median":
                                # Calculate median of this field across all records
                                values = [r.get(field_name) for r in input_data if r.get(field_name) is not None and r.get(field_name) != ""]
                                numeric_vals = sorted([v for v in values if isinstance(v, (int, float))])
                                if numeric_vals:
                                    mid = len(numeric_vals) // 2
                                    if len(numeric_vals) % 2 == 0:
                                        new_record[field_name] = (numeric_vals[mid-1] + numeric_vals[mid]) / 2
                                    else:
                                        new_record[field_name] = numeric_vals[mid]
                                else:
                                    new_record[field_name] = field.get("value", "")
                            elif method == "mode":
                                # Calculate mode of this field across all records
                                values = [r.get(field_name) for r in input_data if r.get(field_name) is not None and r.get(field_name) != ""]
                                if values:
                                    from collections import Counter
                                    counter = Counter(values)
                                    new_record[field_name] = counter.most_common(1)[0][0]
                                else:
                                    new_record[field_name] = field.get("value", "")
                    output_data.append(new_record)
                else:
                    output_data.append(record)
        else:
            # Process single record
            if isinstance(input_data, dict):
                output_data = input_data.copy()
                for field in impute_fields:
                    field_name = field.get("field", "")
                    if field_name in output_data and (output_data[field_name] is None or output_data[field_name] == ""):
                        if method == "fixed":
                            output_data[field_name] = field.get("value", "")
                        else:
                            # For single records, we can't calculate mean/median/mode
                            output_data[field_name] = field.get("value", "")
            else:
                output_data = input_data

        context.node_outputs[node.id] = output_data
        return True

    def _handle_normalize(self, node: PipelineNode, context: PipelineContext) -> bool:
        """Normalize node - normalizes data"""
        config = node.config
        fields_str = config.get("fields", "[]")
        method = config.get("method", "minmax")

        try:
            fields = json.loads(fields_str)
        except json.JSONDecodeError:
            fields = []

        # Get input data from upstream nodes
        input_data = self._get_input_data(node, context)

        if isinstance(input_data, list) and input_data:
            # Collect all values for each field to calculate normalization parameters
            field_stats = {}
            for field_name in fields:
                values = []
                for record in input_data:
                    if isinstance(record, dict) and field_name in record:
                        val = record[field_name]
                        if isinstance(val, (int, float)):
                            values.append(val)

                if values:
                    if method == "minmax":
                        min_val = min(values)
                        max_val = max(values)
                        field_stats[field_name] = {"min": min_val, "max": max_val, "range": max_val - min_val if max_val != min_val else 1}
                    elif method == "zscore":
                        mean_val = sum(values) / len(values)
                        variance = sum((x - mean_val) ** 2 for x in values) / len(values)
                        std_dev = variance ** 0.5
                        field_stats[field_name] = {"mean": mean_val, "std_dev": std_dev if std_dev != 0 else 1}

            # Normalize the data
            output_data = []
            for record in input_data:
                if isinstance(record, dict):
                    new_record = record.copy()
                    for field_name in fields:
                        if field_name in new_record and isinstance(new_record[field_name], (int, float)):
                            val = new_record[field_name]
                            if field_name in field_stats:
                                stats = field_stats[field_name]
                                if method == "minmax":
                                    normalized_val = (val - stats["min"]) / stats["range"]
                                elif method == "zscore":
                                    normalized_val = (val - stats["mean"]) / stats["std_dev"]
                                else:
                                    normalized_val = val  # Default to original value

                                new_record[field_name] = normalized_val
                    output_data.append(new_record)
                else:
                    output_data.append(record)
        else:
            # Single item or empty list - return as is
            output_data = input_data

        context.node_outputs[node.id] = output_data
        return True

    def _handle_outlier(self, node: PipelineNode, context: PipelineContext) -> bool:
        """Outlier node - detects and handles outliers"""
        config = node.config
        fields_str = config.get("fields", "[]")
        method = config.get("method", "iqr")
        action = config.get("action", "flag")

        try:
            fields = json.loads(fields_str)
        except json.JSONDecodeError:
            fields = []

        # Get input data from upstream nodes
        input_data = self._get_input_data(node, context)

        if isinstance(input_data, list) and input_data:
            # Detect outliers for each field
            field_outliers = {}
            for field_name in fields:
                values = []
                for record in input_data:
                    if isinstance(record, dict) and field_name in record:
                        val = record[field_name]
                        if isinstance(val, (int, float)):
                            values.append((len(values), val))  # Store index and value

                if len(values) >= 4:  # Need at least 4 values for meaningful outlier detection
                    sorted_vals = sorted(values, key=lambda x: x[1])
                    n = len(sorted_vals)

                    if method == "iqr":
                        # Calculate quartiles
                        q1_idx = n // 4
                        q3_idx = 3 * n // 4
                        q1 = sorted_vals[q1_idx][1]
                        q3 = sorted_vals[q3_idx][1]
                        iqr = q3 - q1
                        lower_bound = q1 - 1.5 * iqr
                        upper_bound = q3 + 1.5 * iqr

                        outliers = [idx for idx, val in values if val < lower_bound or val > upper_bound]
                    elif method == "zscore":
                        # Calculate z-scores
                        mean_val = sum(v for i, v in values) / len(values)
                        variance = sum((v - mean_val) ** 2 for i, v in values) / len(values)
                        std_dev = variance ** 0.5

                        if std_dev != 0:
                            outliers = [i for i, v in values if abs(v - mean_val) / std_dev > 3]  # Z-score > 3
                        else:
                            outliers = []
                    else:
                        outliers = []

                    field_outliers[field_name] = set(outliers)

            # Process the data based on the action
            if action == "remove":
                output_data = []
                for i, record in enumerate(input_data):
                    is_outlier = any(i in field_outliers.get(field_name, set()) for field_name in fields)
                    if not is_outlier:
                        output_data.append(record)
            elif action == "flag":
                output_data = []
                for i, record in enumerate(input_data):
                    new_record = record.copy() if isinstance(record, dict) else record
                    if isinstance(new_record, dict):
                        is_outlier = any(i in field_outliers.get(field_name, set()) for field_name in fields)
                        new_record["_is_outlier"] = is_outlier
                    output_data.append(new_record)
            elif action == "cap":
                output_data = []
                for i, record in enumerate(input_data):
                    if isinstance(record, dict):
                        new_record = record.copy()
                        for field_name in fields:
                            if field_name in new_record and isinstance(new_record[field_name], (int, float)):
                                if i in field_outliers.get(field_name, set()):
                                    # Cap the value to the bounds
                                    vals = [r[field_name] for r in input_data if isinstance(r, dict) and field_name in r and isinstance(r[field_name], (int, float))]
                                    if vals:
                                        sorted_vals = sorted(vals)
                                        n = len(sorted_vals)
                                        q1 = sorted_vals[n // 4] if n > 0 else new_record[field_name]
                                        q3 = sorted_vals[3 * n // 4] if n > 0 else new_record[field_name]
                                        iqr = q3 - q1
                                        lower_bound = q1 - 1.5 * iqr
                                        upper_bound = q3 + 1.5 * iqr

                                        new_record[field_name] = max(lower_bound, min(upper_bound, new_record[field_name]))
                        output_data.append(new_record)
                    else:
                        output_data.append(record)
            else:
                output_data = input_data
        else:
            # Single item or empty list - return as is
            output_data = input_data

        context.node_outputs[node.id] = output_data
        return True

    def _handle_lookup_table(self, node: PipelineNode, context: PipelineContext) -> bool:
        """Lookup table node - performs database lookups."""
        config = node.config
        lookup_table_str = config.get("lookupTable", "[]")
        join_key = config.get("joinKey", "")

        try:
            lookup_table = json.loads(lookup_table_str)
        except json.JSONDecodeError:
            lookup_table = []

        # Create a lookup map
        lookup_map = {}
        for item in lookup_table:
            if isinstance(item, dict) and join_key in item:
                lookup_map[item[join_key]] = item

        # Get input data from upstream nodes
        input_data = self._get_input_data(node, context)

        if isinstance(input_data, list):
            # Process list of records
            output_data = []
            for record in input_data:
                if isinstance(record, dict) and join_key in record:
                    lookup_value = record[join_key]
                    if lookup_value in lookup_map:
                        # Merge the lookup result with the original record
                        merged_record = record.copy()
                        lookup_result = lookup_map[lookup_value]
                        for k, v in lookup_result.items():
                            if k != join_key:  # Don't overwrite the join key
                                merged_record[f"lookup_{k}"] = v
                        output_data.append(merged_record)
                    else:
                        # No match found, still add the original record
                        record_with_nulls = record.copy()
                        if lookup_table:
                            # Add null values for lookup fields
                            sample_lookup = lookup_table[0] if lookup_table else {}
                            for k in sample_lookup.keys():
                                if k != join_key:
                                    record_with_nulls[f"lookup_{k}"] = None
                        output_data.append(record_with_nulls)
                else:
                    output_data.append(record)
        else:
            # Process single record
            if isinstance(input_data, dict) and join_key in input_data:
                lookup_value = input_data[join_key]
                if lookup_value in lookup_map:
                    # Merge the lookup result with the original record
                    merged_record = input_data.copy()
                    lookup_result = lookup_map[lookup_value]
                    for k, v in lookup_result.items():
                        if k != join_key:  # Don't overwrite the join key
                            merged_record[f"lookup_{k}"] = v
                    output_data = merged_record
                else:
                    # No match found, still return the original record with nulls
                    record_with_nulls = input_data.copy()
                    if lookup_table:
                        # Add null values for lookup fields
                        sample_lookup = lookup_table[0] if lookup_table else {}
                        for k in sample_lookup.keys():
                            if k != join_key:
                                record_with_nulls[f"lookup_{k}"] = None
                    output_data = record_with_nulls
            else:
                output_data = input_data

        context.node_outputs[node.id] = output_data
        return True

    def _handle_api_enrich(self, node: PipelineNode, context: PipelineContext) -> bool:
        """API enrich node - enriches data via API"""
        import requests

        config = node.config
        api_url = config.get("apiUrl", "")
        method = config.get("method", "GET")

        # Get input data from upstream nodes
        input_data = self._get_input_data(node, context)

        if isinstance(input_data, list):
            # Process list of records
            output_data = []
            for record in input_data:
                try:
                    # In a real implementation, we'd use the record data to call the API
                    # For now, we'll just simulate an API call
                    if method.upper() == "GET":
                        # Construct URL with parameters from the record
                        response = requests.get(api_url)
                    elif method.upper() == "POST":
                        response = requests.post(api_url, json=record if isinstance(record, dict) else {})
                    else:
                        response = requests.request(method.upper(), api_url, json=record if isinstance(record, dict) else {})

                    if response.status_code == 200:
                        api_result = response.json()
                        # Merge API result with original record
                        enriched_record = record.copy() if isinstance(record, dict) else {}
                        if isinstance(enriched_record, dict) and isinstance(api_result, dict):
                            for k, v in api_result.items():
                                enriched_record[f"api_{k}"] = v
                        output_data.append(enriched_record)
                    else:
                        # API call failed, still add original record
                        output_data.append(record)
                except Exception as e:
                    logger.error(f"API enrichment error: {e}")
                    context.errors.append(f"API enrichment error: {e}")
                    # Add original record even if API call failed
                    output_data.append(record)
        else:
            # Process single record
            try:
                if method.upper() == "GET":
                    response = requests.get(api_url)
                elif method.upper() == "POST":
                    response = requests.post(api_url, json=input_data if isinstance(input_data, dict) else {})
                else:
                    response = requests.request(method.upper(), api_url, json=input_data if isinstance(input_data, dict) else {})

                if response.status_code == 200:
                    api_result = response.json()
                    # Merge API result with original record
                    if isinstance(input_data, dict):
                        enriched_record = input_data.copy()
                        if isinstance(api_result, dict):
                            for k, v in api_result.items():
                                enriched_record[f"api_{k}"] = v
                        output_data = enriched_record
                    else:
                        output_data = api_result
                else:
                    # API call failed, return original data
                    output_data = input_data
            except Exception as e:
                logger.error(f"API enrichment error: {e}")
                context.errors.append(f"API enrichment error: {e}")
                # Return original data even if API call failed
                output_data = input_data

        context.node_outputs[node.id] = output_data
        return True

    def _handle_delay(self, node: PipelineNode, context: PipelineContext) -> bool:
        """Delay node - delays processing"""
        import time

        config = node.config
        duration = config.get("duration", 5)  # seconds
        unit = config.get("unit", "seconds")

        # Convert to seconds
        if unit == "milliseconds":
            duration = duration / 1000.0
        elif unit == "minutes":
            duration = duration * 60.0
        elif unit == "hours":
            duration = duration * 3600.0

        # Sleep for the specified duration
        time.sleep(duration)

        # Pass through the input data unchanged
        input_data = self._get_input_data(node, context)
        context.node_outputs[node.id] = input_data
        return True

    def _handle_cache(self, node: PipelineNode, context: PipelineContext) -> bool:
        """Cache node - caches data for reuse"""
        config = node.config
        ttl = config.get("ttl", 3600)  # Time to live in seconds

        # Get input data from upstream nodes
        input_data = self._get_input_data(node, context)

        # In a real implementation, we'd store this in a cache with TTL
        # For now, we'll just pass the data through
        context.node_outputs[node.id] = input_data
        return True

    def _handle_read_json(self, node: PipelineNode, context: PipelineContext) -> bool:
        """Read JSON node"""
        config = node.config
        file_path = config.get("path", "")
        array_path = config.get("arrayPath", "")

        if file_path:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)

                # If array_path is specified, extract that part of the JSON
                if array_path:
                    # Simple implementation - in reality, we'd use JSONPath
                    keys = array_path.split('.')
                    for key in keys:
                        if isinstance(data, dict) and key in data:
                            data = data[key]
                        else:
                            break

                context.node_outputs[node.id] = data
            except Exception as e:
                logger.error(f"Read JSON error: {e}")
                context.errors.append(f"Read JSON error: {e}")
                return False
        else:
            # Get data from upstream nodes if no file path specified
            input_data = self._get_input_data(node, context)
            context.node_outputs[node.id] = input_data

        return True

    def _handle_write_json(self, node: PipelineNode, context: PipelineContext) -> bool:
        """Write JSON node"""
        config = node.config
        file_path = config.get("path", "")
        root_key = config.get("rootKey", "")
        pretty = config.get("pretty", True)

        # Get input data from upstream nodes
        input_data = self._get_input_data(node, context)

        if file_path:
            try:
                # Optionally wrap data in a root key
                output_data = input_data
                if root_key:
                    output_data = {root_key: input_data}

                # Write to file
                with open(file_path, 'w') as f:
                    if pretty:
                        json.dump(output_data, f, indent=2)
                    else:
                        json.dump(output_data, f)
            except Exception as e:
                logger.error(f"Write JSON error: {e}")
                context.errors.append(f"Write JSON error: {e}")
                return False
        # If no file path, just store in context for downstream nodes

        context.node_outputs[node.id] = input_data
        return True

    def _handle_read_excel(self, node: PipelineNode, context: PipelineContext) -> bool:
        """Read Excel node"""
        config = node.config
        file_path = config.get("path", "")
        sheet_name = config.get("sheetName", "Sheet1")
        has_header = config.get("hasHeader", True)

        if file_path:
            try:
                import pandas as pd

                # Read Excel file
                df = pd.read_excel(file_path, sheet_name=sheet_name, header=0 if has_header else None)

                # Convert to list of dictionaries (records)
                data = df.to_dict('records') if has_header else df.values.tolist()

                context.node_outputs[node.id] = data
            except ImportError:
                logger.error("pandas not available for Excel reading")
                context.errors.append("pandas not available for Excel reading")
                return False
            except Exception as e:
                logger.error(f"Read Excel error: {e}")
                context.errors.append(f"Read Excel error: {e}")
                return False
        else:
            # Get data from upstream nodes if no file path specified
            input_data = self._get_input_data(node, context)
            context.node_outputs[node.id] = input_data

        return True

    def _handle_write_excel(self, node: PipelineNode, context: PipelineContext) -> bool:
        """Write Excel node"""
        config = node.config
        file_path = config.get("path", "")
        sheet_name = config.get("sheetName", "Sheet1")

        # Get input data from upstream nodes
        input_data = self._get_input_data(node, context)

        if file_path:
            try:
                import pandas as pd

                # Convert data to DataFrame
                if isinstance(input_data, list):
                    df = pd.DataFrame(input_data)
                else:
                    df = pd.DataFrame([input_data] if input_data else [])

                # Write to Excel file
                df.to_excel(file_path, sheet_name=sheet_name, index=False)
            except ImportError:
                logger.error("pandas not available for Excel writing")
                context.errors.append("pandas not available for Excel writing")
                return False
            except Exception as e:
                logger.error(f"Write Excel error: {e}")
                context.errors.append(f"Write Excel error: {e}")
                return False

        context.node_outputs[node.id] = input_data
        return True

    def _handle_profile(self, node: PipelineNode, context: PipelineContext) -> bool:
        """Profile node - generates data profile"""
        config = node.config
        format_type = config.get("format", "csv")
        field_mapping_str = config.get("fieldMapping", "[]")

        try:
            field_mapping = json.loads(field_mapping_str)
        except json.JSONDecodeError:
            field_mapping = []

        # Get input data from upstream nodes
        input_data = self._get_input_data(node, context)

        # Generate profile statistics
        if isinstance(input_data, list) and input_data:
            profile = {
                "total_records": len(input_data),
                "fields": {},
                "summary": {}
            }

            if isinstance(input_data[0], dict):  # List of dictionaries
                # Get all unique field names
                all_fields = set()
                for record in input_data:
                    if isinstance(record, dict):
                        all_fields.update(record.keys())

                for field in all_fields:
                    values = [record.get(field) for record in input_data if isinstance(record, dict)]
                    non_null_values = [v for v in values if v is not None and v != ""]

                    field_profile = {
                        "total_count": len(values),
                        "non_null_count": len(non_null_values),
                        "null_count": len(values) - len(non_null_values),
                        "unique_count": len(set(str(v) for v in non_null_values)),
                    }

                    # Try to determine data type and add appropriate statistics
                    numeric_values = []
                    string_values = []

                    for v in non_null_values:
                        if isinstance(v, (int, float)):
                            numeric_values.append(v)
                        else:
                            try:
                                num_v = float(v)
                                numeric_values.append(num_v)
                            except (ValueError, TypeError):
                                string_values.append(str(v))

                    if numeric_values:
                        field_profile["type"] = "numeric"
                        field_profile["min"] = min(numeric_values)
                        field_profile["max"] = max(numeric_values)
                        field_profile["mean"] = sum(numeric_values) / len(numeric_values)
                        field_profile["std_dev"] = (sum((x - field_profile["mean"]) ** 2 for x in numeric_values) / len(numeric_values)) ** 0.5
                    elif string_values:
                        field_profile["type"] = "string"
                        field_profile["min_length"] = min(len(s) for s in string_values) if string_values else 0
                        field_profile["max_length"] = max(len(s) for s in string_values) if string_values else 0
                        field_profile["avg_length"] = sum(len(s) for s in string_values) / len(string_values) if string_values else 0
                    else:
                        field_profile["type"] = "other"

                    profile["fields"][field] = field_profile

            context.node_outputs[node.id] = profile
        else:
            # Single item or empty list - return basic info
            context.node_outputs[node.id] = {
                "total_records": 1 if input_data else 0,
                "fields": {},
                "summary": {"type": type(input_data).__name__}
            }

        return True

    def _handle_query(self, node: PipelineNode, context: PipelineContext) -> bool:
        """Query node - executes queries (SQL, Python, etc.)"""
        config = node.config
        query_type = config.get("queryType", "sql")
        mode = config.get("mode", "transform")
        query = config.get("query", "")

        # Get input data from upstream nodes
        input_data = self._get_input_data(node, context)

        if query_type == "python":
            try:
                # Execute Python code in a restricted environment
                # In a real implementation, use a safer execution method
                local_vars = {"input": input_data, "context": context}
                exec(query, {"__builtins__": {}}, local_vars)

                if "output" in local_vars:
                    result = local_vars["output"]
                else:
                    result = input_data  # Default to input if no output defined

            except Exception as e:
                logger.error(f"Python query execution error: {e}")
                context.errors.append(f"Python query execution error: {e}")
                return False
        else:
            # For other query types (SQL), we would connect to a database
            # This is a simplified implementation
            result = input_data

        context.node_outputs[node.id] = result
        return True

    def execute(self, input_file: Path, output_file: Path) -> bool:
        """Execute the pipeline with enhanced error handling and metrics"""
        # Load and parse pipeline
        pipeline_data = self.load_pipeline()
        self.parse_pipeline(pipeline_data)

        # Create context before validation so we can use add_error method
        self.context = PipelineContext(input_file=input_file, output_file=output_file)

        # Validate pipeline before execution
        validation_errors = self.validate_pipeline()
        if validation_errors:
            logger.error("Pipeline validation failed:")
            for error in validation_errors:
                logger.error(f"- {error['error']} ({error['error_type']})")
                self.context.add_error("validation", error["error"], error["error_type"])
            return False

        self.context.variables["start_time"] = datetime.now()
        logger.info(f"Starting pipeline execution at {self.context.variables['start_time']}")

        # Get execution order
        execution_order = self.get_execution_order()
        logger.info(f"Execution order: {execution_order}")

        # Execute each node
        for node_id in execution_order:
            if self.context.canceled:
                logger.warning("Pipeline execution canceled")
                return False

            logger.info(f"Executing node: {node_id}")
            start_time = datetime.now()
            
            try:
                self.context.increment_node_attempts(node_id)
                success = self.execute_node(node_id, self.context)
                
                # Calculate and store execution time
                execution_time = (datetime.now() - start_time).total_seconds()
                self.context.set_node_execution_time(node_id, execution_time)
                logger.info(f"Node {node_id} executed in {execution_time:.2f} seconds")
                
                if not success:
                    logger.error(f"Node {node_id} execution failed")
                    return False
                    
            except Exception as e:
                logger.error(f"Unhandled exception in node {node_id}: {e}")
                self.context.add_error(node_id, str(e), "critical")
                return False

        # Calculate total execution time
        total_time = (datetime.now() - self.context.variables["start_time"]).total_seconds()
        self.context.pipeline_metrics["total_execution_time"] = total_time
        self.context.pipeline_metrics["node_count"] = len(execution_order)
        self.context.pipeline_metrics["error_count"] = len(self.context.errors)
        
        logger.info(f"Pipeline execution completed in {total_time:.2f} seconds")
        logger.info(f"Total nodes executed: {len(execution_order)}")
        logger.info(f"Errors encountered: {len(self.context.errors)}")

        return len(self.context.errors) == 0

    def _get_input_data(self, node: PipelineNode, context: PipelineContext):
        """Get input data from upstream nodes connected to this node"""
        # Look for incoming edges to this node
        input_data = None

        for edge in self.edges:
            if edge.get("target") == node.id:
                source_node_id = edge.get("source")
                if source_node_id in context.node_outputs:
                    # Get the data from the source node
                    source_data = context.node_outputs[source_node_id]

                    # For router nodes, they output to specific handles like "node_id_true" or "node_id_false"
                    if source_node_id.endswith("_true") or source_node_id.endswith("_false"):
                        # This is already a routed output
                        input_data = source_data
                    else:
                        input_data = source_data
                    break  # For simplicity, taking the first input

        # If no upstream data found, return empty/default
        if input_data is None:
            input_data = context.current_data or ""

        return input_data

    def _get_upstream_nodes(self, node_id: str) -> List[str]:
        """Get IDs of upstream nodes that feed into the given node"""
        upstream_ids = []
        for edge in self.edges:
            if edge.get("target") == node_id:
                source_id = edge.get("source")
                if source_id:
                    upstream_ids.append(source_id)
        return upstream_ids


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description="Execute pipeline DAG")
    parser.add_argument("--pipeline", required=True, help="Pipeline JSON file")
    parser.add_argument("--input", required=True, help="Input EDI file")
    parser.add_argument("--output", required=True, help="Output file")
    args = parser.parse_args()

    executor = PipelineExecutor(Path(args.pipeline))
    success = executor.execute(Path(args.input), Path(args.output))

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

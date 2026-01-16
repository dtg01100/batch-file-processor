#!/usr/bin/env python3
"""
Tests for pipeline executor functionality.
"""

import sys
import tempfile
import pytest
import json
import os
from pathlib import Path

# Add project root to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.pipeline_executor import PipelineExecutor, PipelineContext


def test_pipeline_executor_initialization():
    """Test that PipelineExecutor can be initialized."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump({
            "nodes": [
                {"id": "start", "type": "start", "data": {"label": "Start"}},
                {"id": "end", "type": "end", "data": {"label": "End"}}
            ],
            "edges": [
                {"source": "start", "target": "end"}
            ]
        }, f)
        temp_file = f.name
    
    try:
        executor = PipelineExecutor(Path(temp_file))
        assert isinstance(executor, PipelineExecutor)
    finally:
        try:
            os.unlink(temp_file)
        except OSError:
            pass


def test_load_pipeline():
    """Test that pipeline can be loaded from JSON file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump({
            "nodes": [
                {"id": "start", "type": "start", "data": {"label": "Start"}},
                {"id": "end", "type": "end", "data": {"label": "End"}}
            ],
            "edges": [
                {"source": "start", "target": "end"}
            ]
        }, f)
        temp_file = f.name
    
    try:
        executor = PipelineExecutor(Path(temp_file))
        pipeline_data = executor.load_pipeline()
        assert isinstance(pipeline_data, dict)
        assert "nodes" in pipeline_data
        assert "edges" in pipeline_data
    finally:
        try:
            os.unlink(temp_file)
        except OSError:
            pass


def test_parse_pipeline():
    """Test that pipeline can be parsed into node objects."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump({
            "nodes": [
                {"id": "start", "type": "start", "data": {"label": "Start"}},
                {"id": "end", "type": "end", "data": {"label": "End"}}
            ],
            "edges": [
                {"source": "start", "target": "end"}
            ]
        }, f)
        temp_file = f.name
    
    try:
        executor = PipelineExecutor(Path(temp_file))
        pipeline_data = executor.load_pipeline()
        nodes = executor.parse_pipeline(pipeline_data)
        assert len(nodes) == 2  # start and end nodes
        node_ids = [node.id for node in nodes]
        assert "start" in node_ids
        assert "end" in node_ids
    finally:
        try:
            os.unlink(temp_file)
        except OSError:
            pass


def test_validate_pipeline():
    """Test that pipeline validation works correctly."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump({
            "nodes": [
                {"id": "start", "type": "start", "data": {"label": "Start"}},
                {"id": "end", "type": "end", "data": {"label": "End"}}
            ],
            "edges": [
                {"source": "start", "target": "end"}
            ]
        }, f)
        temp_file = f.name
    
    try:
        executor = PipelineExecutor(Path(temp_file))
        pipeline_data = executor.load_pipeline()
        executor.parse_pipeline(pipeline_data)
        errors = executor.validate_pipeline()
        assert len(errors) == 0, f"Pipeline validation failed: {errors}"
    finally:
        try:
            os.unlink(temp_file)
        except OSError:
            pass


def test_get_execution_order():
    """Test that execution order is correctly determined using Kahn's algorithm."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump({
            "nodes": [
                {"id": "start", "type": "start", "data": {"label": "Start"}},
                {"id": "end", "type": "end", "data": {"label": "End"}}
            ],
            "edges": [
                {"source": "start", "target": "end"}
            ]
        }, f)
        temp_file = f.name
    
    try:
        executor = PipelineExecutor(Path(temp_file))
        pipeline_data = executor.load_pipeline()
        executor.parse_pipeline(pipeline_data)
        order = executor.get_execution_order()
        assert isinstance(order, list)
        assert len(order) == 2
        assert order[0] == "start"
        assert order[1] == "end"
    finally:
        try:
            os.unlink(temp_file)
        except OSError:
            pass


def test_pipeline_context_creation():
    """Test that PipelineContext can be created."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.edi', delete=False, encoding='utf-8') as f:
        f.write("TEST EDI DATA")
        input_file = f.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        output_file = f.name
    
    try:
        context = PipelineContext(input_file=Path(input_file), output_file=Path(output_file))
        assert isinstance(context, PipelineContext)
        assert str(context.input_file) == str(input_file)
        assert str(context.output_file) == str(output_file)
        assert context.current_data is None
        assert context.variables == {}
        assert context.errors == []
        assert context.node_outputs == {}
        assert context.node_execution_times == {}
        assert context.node_attempts == {}
        assert context.pipeline_metrics == {}
        assert context.canceled is False
    finally:
        try:
            os.unlink(input_file)
        except OSError:
            pass
        try:
            os.unlink(output_file)
        except OSError:
            pass


def test_context_add_error():
    """Test that errors can be added to pipeline context."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.edi', delete=False, encoding='utf-8') as f:
        f.write("TEST EDI DATA")
        input_file = f.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        output_file = f.name
    
    try:
        context = PipelineContext(input_file=Path(input_file), output_file=Path(output_file))
        context.add_error("test_node", "Test error message")
        assert len(context.errors) == 1
        error = context.errors[0]
        assert error["node_id"] == "test_node"
        assert error["error"] == "Test error message"
        assert error["error_type"] == "error"
        assert "timestamp" in error
    finally:
        try:
            os.unlink(input_file)
        except OSError:
            pass
        try:
            os.unlink(output_file)
        except OSError:
            pass


def test_context_node_execution_time():
    """Test that node execution time can be set and retrieved."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.edi', delete=False, encoding='utf-8') as f:
        f.write("TEST EDI DATA")
        input_file = f.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        output_file = f.name
    
    try:
        context = PipelineContext(input_file=Path(input_file), output_file=Path(output_file))
        context.set_node_execution_time("test_node", 1.5)
        assert "test_node" in context.node_execution_times
        assert context.node_execution_times["test_node"] == 1.5
    finally:
        try:
            os.unlink(input_file)
        except OSError:
            pass
        try:
            os.unlink(output_file)
        except OSError:
            pass


def test_context_node_attempts():
    """Test that node attempts can be tracked."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.edi', delete=False, encoding='utf-8') as f:
        f.write("TEST EDI DATA")
        input_file = f.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        output_file = f.name
    
    try:
        context = PipelineContext(input_file=Path(input_file), output_file=Path(output_file))
        context.increment_node_attempts("test_node")
        assert context.get_node_attempts("test_node") == 1
        context.increment_node_attempts("test_node")
        assert context.get_node_attempts("test_node") == 2
    finally:
        try:
            os.unlink(input_file)
        except OSError:
            pass
        try:
            os.unlink(output_file)
        except OSError:
            pass


def test_execute_simple_pipeline():
    """Test executing a simple pipeline with start and end nodes."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump({
            "nodes": [
                {"id": "start", "type": "start", "data": {"label": "Start"}},
                {"id": "end", "type": "end", "data": {"label": "End"}}
            ],
            "edges": [
                {"source": "start", "target": "end"}
            ]
        }, f)
        pipeline_file = f.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.edi', delete=False, encoding='utf-8') as f:
        f.write("TEST EDI DATA")
        input_file = f.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        output_file = f.name
    
    try:
        executor = PipelineExecutor(Path(pipeline_file))
        success = executor.execute(Path(input_file), Path(output_file))
        assert success is True
    finally:
        try:
            os.unlink(pipeline_file)
        except OSError:
            pass
        try:
            os.unlink(input_file)
        except OSError:
            pass
        try:
            os.unlink(output_file)
        except OSError:
            pass


def test_execute_pipeline_with_invalid_nodes():
    """Test pipeline execution with invalid node configuration."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump({
            "nodes": [
                {"id": "invalid", "type": "invalidNodeType", "data": {"label": "Invalid Node"}},
                {"id": "end", "type": "end", "data": {"label": "End"}}
            ],
            "edges": [
                {"source": "invalid", "target": "end"}
            ]
        }, f)
        pipeline_file = f.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.edi', delete=False, encoding='utf-8') as f:
        f.write("TEST EDI DATA")
        input_file = f.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        output_file = f.name
    
    try:
        executor = PipelineExecutor(Path(pipeline_file))
        success = executor.execute(Path(input_file), Path(output_file))
        assert success is False
    finally:
        try:
            os.unlink(pipeline_file)
        except OSError:
            pass
        try:
            os.unlink(input_file)
        except OSError:
            pass
        try:
            os.unlink(output_file)
        except OSError:
            pass

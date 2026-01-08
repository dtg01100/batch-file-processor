"""Pipeline Graph API

REST endpoints for saving, loading, and managing pipeline graphs
for the visual pipeline editor.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.database import get_database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


class PipelineNode(BaseModel):
    """Pipeline node model"""

    id: str
    type: str  # folderInput, job, profile, output
    position: Dict[str, float]  # {x, y}
    data: Dict[str, Any]


class PipelineEdge(BaseModel):
    """Pipeline edge model"""

    id: str
    source: str
    target: str
    type: str = "smoothstep"


class PipelineCreate(BaseModel):
    """Pipeline creation model"""

    name: str
    description: Optional[str] = ""
    nodes: List[PipelineNode]
    edges: List[PipelineEdge]
    is_template: bool = False


class PipelineUpdate(BaseModel):
    """Pipeline update model"""

    name: Optional[str] = None
    description: Optional[str] = None
    nodes: Optional[List[PipelineNode]] = None
    edges: Optional[List[PipelineEdge]] = None
    is_template: Optional[bool] = None


@router.get("/")
def list_pipelines():
    """
    List all pipelines

    Returns list of all saved pipelines
    """
    db = get_database()
    pipelines_table = db["pipelines"]

    pipelines = list(pipelines_table.all())

    return {
        "pipelines": [
            {
                "id": p["id"],
                "name": p["name"],
                "description": p.get("description", ""),
                "is_template": p.get("is_template", False),
                "node_count": len(p.get("nodes", [])),
                "created_at": p.get("created_at"),
                "updated_at": p.get("updated_at"),
            }
            for p in pipelines
        ]
    }


@router.get("/{pipeline_id}")
def get_pipeline(pipeline_id: int):
    """
    Get specific pipeline by ID

    Returns full pipeline with nodes and edges
    """
    db = get_database()
    pipelines_table = db["pipelines"]

    pipeline = pipelines_table.find_one(id=pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    return {
        "id": pipeline["id"],
        "name": pipeline["name"],
        "description": pipeline.get("description", ""),
        "nodes": pipeline.get("nodes", []),
        "edges": pipeline.get("edges", []),
        "is_template": pipeline.get("is_template", False),
        "created_at": pipeline.get("created_at"),
        "updated_at": pipeline.get("updated_at"),
    }


@router.post("/")
def create_pipeline(pipeline: PipelineCreate):
    """
    Create new pipeline

    Creates a new pipeline from graph data
    """
    db = get_database()
    pipelines_table = db["pipelines"]

    pipeline_id = pipelines_table.insert(
        {
            "name": pipeline.name,
            "description": pipeline.description,
            "nodes": [n.dict() for n in pipeline.nodes],
            "edges": [e.dict() for e in pipeline.edges],
            "is_template": pipeline.is_template,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
    )

    logger.info(f"Pipeline created: {pipeline.name} (ID: {pipeline_id})")

    return {
        "id": pipeline_id,
        "name": pipeline.name,
        "message": "Pipeline created successfully",
    }


@router.put("/{pipeline_id}")
def update_pipeline(pipeline_id: int, update: PipelineUpdate):
    """
    Update existing pipeline

    Updates pipeline fields (name, description, nodes, edges)
    """
    db = get_database()
    pipelines_table = db["pipelines"]

    pipeline = pipelines_table.find_one(id=pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    update_dict = {"updated_at": datetime.now()}

    if update.name is not None:
        update_dict["name"] = update.name
    if update.description is not None:
        update_dict["description"] = update.description
    if update.nodes is not None:
        update_dict["nodes"] = [n.dict() for n in update.nodes]
    if update.edges is not None:
        update_dict["edges"] = [e.dict() for e in update.edges]
    if update.is_template is not None:
        update_dict["is_template"] = update.is_template

    pipelines_table.update(update_dict, ["id"])

    logger.info(f"Pipeline updated: {pipeline_id}")

    return {"message": "Pipeline updated successfully"}


@router.delete("/{pipeline_id}")
def delete_pipeline(pipeline_id: int):
    """
    Delete pipeline

    Removes pipeline from database
    """
    db = get_database()
    pipelines_table = db["pipelines"]

    pipeline = pipelines_table.find_one(id=pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    pipelines_table.delete(id=pipeline_id)

    logger.info(f"Pipeline deleted: {pipeline_id}")

    return {"message": "Pipeline deleted successfully"}


@router.get("/templates")
def list_templates():
    """
    List pipeline templates

    Returns all pipelines marked as templates
    """
    db = get_database()
    pipelines_table = db["pipelines"]

    templates = list(pipelines_table.find(is_template=True))

    return {
        "templates": [
            {
                "id": t["id"],
                "name": t["name"],
                "description": t.get("description", ""),
                "node_count": len(t.get("nodes", [])),
            }
            for t in templates
        ]
    }


@router.post("/{pipeline_id}/duplicate")
def duplicate_pipeline(pipeline_id: int):
    """
    Duplicate pipeline

    Creates a copy of existing pipeline with new ID
    """
    db = get_database()
    pipelines_table = db["pipelines"]

    pipeline = pipelines_table.find_one(id=pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    new_id = pipelines_table.insert(
        {
            "name": f"{pipeline['name']} (Copy)",
            "description": pipeline.get("description", ""),
            "nodes": pipeline.get("nodes", []),
            "edges": pipeline.get("edges", []),
            "is_template": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
    )

    logger.info(f"Pipeline duplicated: {pipeline_id} -> {new_id}")

    return {
        "id": new_id,
        "name": f"{pipeline['name']} (Copy)",
        "message": "Pipeline duplicated successfully",
    }


@router.get("/{pipeline_id}/export")
def export_pipeline(pipeline_id: int):
    """
    Export pipeline as JSON

    Returns pipeline data for download/import elsewhere
    """
    db = get_database()
    pipelines_table = db["pipelines"]

    pipeline = pipelines_table.find_one(id=pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    return {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "pipeline": {
            "name": pipeline["name"],
            "description": pipeline.get("description", ""),
            "nodes": pipeline.get("nodes", []),
            "edges": pipeline.get("edges", []),
        },
    }


@router.post("/import")
def import_pipeline(data: Dict):
    """
    Import pipeline from JSON

    Creates new pipeline from exported data
    """
    if "pipeline" not in data:
        raise HTTPException(status_code=400, detail="Invalid import data")

    pipeline_data = data["pipeline"]

    db = get_database()
    pipelines_table = db["pipelines"]

    pipeline_id = pipelines_table.insert(
        {
            "name": pipeline_data.get("name", "Imported Pipeline"),
            "description": pipeline_data.get("description", ""),
            "nodes": pipeline_data.get("nodes", []),
            "edges": pipeline_data.get("edges", []),
            "is_template": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
    )

    logger.info(f"Pipeline imported: {pipeline_id}")

    return {
        "id": pipeline_id,
        "name": pipeline_data.get("name", "Imported Pipeline"),
        "message": "Pipeline imported successfully",
    }

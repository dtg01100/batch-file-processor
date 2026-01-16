# Batch File Processor

A comprehensive system for processing EDI and other batch files with a visual pipeline editor.

## Overview

This project provides a modern, web-based interface for processing batch files (particularly EDI files) with a visual pipeline editor. The system allows users to create complex data processing workflows using a drag-and-drop interface, replacing the older script-based approach.

## Architecture

The system consists of:

- **Frontend**: React-based visual pipeline editor using React Flow
- **Backend**: FastAPI-based service with pipeline execution engine
- **Database**: SQLite for storing configurations and job histories
- **Pipeline Engine**: Executes visual pipelines with 30+ different node types

## Visual Pipeline System

The new visual pipeline system allows users to create data processing workflows by connecting different types of nodes:

### Node Types

- **Sources**: Input source nodes for reading files from local/SMB/SFTP locations
- **Transforms**: Data transformation nodes (remapping, filtering, joining, aggregating, etc.)
- **Quality**: Data validation, imputation, normalization, and outlier detection
- **Enrichment**: Lookup tables and API enrichment
- **Outputs**: Output destination nodes for writing results

### Pipeline Execution

Pipelines are executed as directed acyclic graphs (DAGs) where data flows from source nodes through transformation nodes to output nodes. The PipelineExecutor handles the execution of each node in the correct order.

## Legacy Scripts

The project still maintains legacy conversion scripts (convert_to_*.py) for backward compatibility, but new functionality should be implemented using the visual pipeline system.

## Setup

### Prerequisites

- Python 3.8+
- Node.js 16+
- Docker (optional, for containerized deployment)

### Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Navigate to the frontend directory and install dependencies:
   ```bash
   cd frontend
   npm install
   ```
5. Build the frontend:
   ```bash
   npm run build
   ```

### Running the Application

#### Development Mode

Backend:
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend (separate terminal):
```bash
cd frontend
npm run dev
```

#### Production Mode

Using Docker:
```bash
docker-compose -f docker/docker-compose.yml up
```

## Pipeline Examples

The system includes several example pipelines in the `pipelines/examples/` directory:

- `complete_edi_pipeline.json`: Full EDI processing pipeline with validation, transformation, and delivery
- `edi_to_standard_csv.json`: Converts EDI to standard CSV format
- `edi_to_fintech.json`: Converts EDI to Fintech-specific format
- `edi_to_scannerware.json`: Converts EDI to Scannerware format

## Creating Custom Pipelines

1. Access the Pipeline Editor through the web interface
2. Drag nodes from the sidebar onto the canvas
3. Connect nodes by dragging from output handles to input handles
4. Configure each node by selecting it and adjusting properties in the right panel
5. Save the pipeline and execute it

## Testing

Run backend tests:
```bash
pytest -v
```

Run frontend tests:
```bash
cd frontend
npm run test
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

[Specify license here]

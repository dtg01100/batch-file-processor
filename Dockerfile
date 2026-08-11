# Batch File Sender — local webapp image.
#
# The desktop (Qt/PySide6) app and its frozen-binary build machinery were
# removed in the webapp pivot; this image runs the FastAPI webapp that
# drives the same dispatch pipeline.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    BFS_BASE_DIR=/data \
    BFS_DATA_DIR=/data/config

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

EXPOSE 8000

CMD ["python", "-m", "webapp.main"]

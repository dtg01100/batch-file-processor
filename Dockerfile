FROM mcr.microsoft.com/devcontainers/python:1-3.11-bookworm

RUN apt-get update && apt-get upgrade -y
RUN apt-get -f install -y
RUN apt-get -y install build-essential sqlite3 python3-tk
COPY ibm-iaccess-1.1.0.28-1.0.amd64.deb /tmp/ibm-iaccess-1.1.0.28-1.0.amd64.deb
RUN apt-get -y install /tmp/ibm-iaccess-1.1.0.28-1.0.amd64.deb && apt-get -f install -y

COPY requirements.txt /tmp/pip-tmp/
RUN pip3 --disable-pip-version-check --no-cache-dir install --break-system-packages -r /tmp/pip-tmp/requirements.txt \
&& rm -rf /tmp/pip-tmp

FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

RUN apt-get update && apt-get upgrade -y
RUN apt-get -f install -y
RUN apt-get -y install python3-pip python3-tk python3-dev build-essential python3-wheel
COPY ibm-iaccess-1.1.0.28-1.0.amd64.deb /tmp/ibm-iaccess-1.1.0.28-1.0.amd64.deb
RUN apt-get -y install /tmp/ibm-iaccess-1.1.0.28-1.0.amd64.deb
RUN apt-get -f install -y

COPY requirements.txt /tmp/pip-tmp/
RUN pip3 --disable-pip-version-check --no-cache-dir install --break-system-packages -r /tmp/pip-tmp/requirements.txt \
&& rm -rf /tmp/pip-tmp

FROM mcr.microsoft.com/devcontainers/python:1-3.11-bookworm

# Fix yarn GPG key issue (key 62D54FD4003F6525 is missing in base image)
RUN curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | gpg --dearmor -o /usr/share/keyrings/yarnkey.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/yarnkey.gpg] https://dl.yarnpkg.com/debian stable main" > /etc/apt/sources.list.d/yarn.list

RUN apt-get update && apt-get upgrade -y
RUN apt-get -f install -y
RUN apt-get -y install \
    build-essential \
    sqlite3 \
    python3-tk \
    xvfb \
    x11vnc \
    websockify \
    git \
    openbox \
    libegl1 \
    libgl1 \
    libglib2.0-0 \
    libxkbcommon-x11-0 \
    libdbus-1-3 \
    libfontconfig1 \
    libxrender1 \
    libxcb-cursor0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-xfixes0 \
    libxcb-xinerama0 \
    libxcb-xkb1
# Clone noVNC for browser-based X11 viewing
RUN git clone https://github.com/novnc/noVNC.git /tmp/novnc

COPY requirements.txt /tmp/pip-tmp/
RUN pip3 --disable-pip-version-check --no-cache-dir install --break-system-packages -r /tmp/pip-tmp/requirements.txt \
&& rm -rf /tmp/pip-tmp

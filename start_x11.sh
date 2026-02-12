#!/bin/bash
# Start X11 VNC server with window manager for browser viewing

# Unset WAYLAND_DISPLAY to avoid conflicts
unset WAYLAND_DISPLAY

# Kill existing processes
pkill Xvfb 2>/dev/null || true
pkill x11vnc 2>/dev/null || true
pkill websockify 2>/dev/null || true
pkill openbox 2>/dev/null || true

# Start Xvfb
Xvfb :99 -screen 0 1024x768x24 +extension GLX +render -noreset > /tmp/xvfb.log 2>&1 &
sleep 1

# Start Openbox window manager
openbox &
sleep 1

# Start x11vnc
x11vnc -display :99 -forever -shared -rfbport 5900 -nopw > /tmp/x11vnc.log 2>&1 &
sleep 1

# Start websockify
websockify --web /tmp/novnc 0.0.0.0:6080 localhost:5900 > /tmp/websockify.log 2>&1 &

echo "X11 services started with Openbox window manager"
echo "Access noVNC at: http://localhost:6080/vnc.html"
echo "Run GUI apps with: DISPLAY=:99 python main_interface.py"

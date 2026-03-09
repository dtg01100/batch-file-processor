#!/bin/bash
# Start X11 VNC server with window manager for browser viewing
#
# Services managed:
#   Xvfb       – virtual framebuffer on DISPLAY :99
#   openbox    – lightweight window manager
#   x11vnc     – VNC server on port 5900
#   websockify – WebSocket proxy (noVNC) on port 6080
#
# The script is idempotent: safe to call from postStartCommand and
# postAttachCommand — it only (re)starts services that aren't running.

set -euo pipefail

# Unset WAYLAND_DISPLAY to avoid conflicts
unset WAYLAND_DISPLAY

DISPLAY_NUM=":99"
XVFB_LOG="/tmp/xvfb.log"
OPENBOX_LOG="/tmp/openbox.log"
X11VNC_LOG="/tmp/x11vnc.log"
WEBSOCKIFY_LOG="/tmp/websockify.log"
WEBSOCKIFY_PATTERN="websockify.*0.0.0.0:6080.*localhost:5900"

# ── helpers ────────────────────────────────────────────────────────────

ensure_novnc_ready() {
    local retries=10
    local delay=1
    local i

    for i in $(seq 1 "$retries"); do
        if curl --max-time 2 -fsS -I http://127.0.0.1:6080/vnc.html > /dev/null 2>&1; then
            return 0
        fi
        sleep "$delay"
    done

    echo "noVNC endpoint not ready after ${retries}s; restarting websockify once..."
    pkill -f "$WEBSOCKIFY_PATTERN" || true
    sleep 1
    setsid websockify --web /tmp/noVNC 0.0.0.0:6080 localhost:5900 > "$WEBSOCKIFY_LOG" 2>&1 &
    disown

    for i in $(seq 1 "$retries"); do
        if curl --max-time 2 -fsS -I http://127.0.0.1:6080/vnc.html > /dev/null 2>&1; then
            return 0
        fi
        sleep "$delay"
    done

    echo "noVNC endpoint still not ready; check $WEBSOCKIFY_LOG"
    return 1
}

start_openbox() {
    if ! pgrep -x "openbox" > /dev/null; then
        echo "Starting openbox..."
        setsid openbox > "$OPENBOX_LOG" 2>&1 &
        disown
        sleep 1
    fi
}

start_x11vnc() {
    if ! pgrep -x "x11vnc" > /dev/null; then
        echo "Starting x11vnc..."
        # Use x11vnc's native -bg flag so it daemonises itself properly
        # and survives the parent shell exiting.
        x11vnc -display "$DISPLAY_NUM" -forever -shared -rfbport 5900 \
               -nopw -bg -o "$X11VNC_LOG" 2>&1
        sleep 1
    fi
}

start_websockify() {
    # Kill duplicates first
    if [ "$(pgrep -fc "$WEBSOCKIFY_PATTERN" 2>/dev/null || echo 0)" -gt 1 ]; then
        pkill -f "$WEBSOCKIFY_PATTERN" || true
        sleep 1
    fi
    if ! pgrep -f "$WEBSOCKIFY_PATTERN" > /dev/null 2>&1; then
        echo "Starting websockify..."
        setsid websockify --web /tmp/noVNC 0.0.0.0:6080 localhost:5900 \
               > "$WEBSOCKIFY_LOG" 2>&1 &
        disown
        sleep 1
    fi
}

# ── main ───────────────────────────────────────────────────────────────

# Check if Xvfb is already running
if pgrep -x "Xvfb" > /dev/null; then
    echo "X11 (Xvfb) is already running"
else
    # Ensure noVNC web assets are available (prefer pre-baked image copy, then clone)
    if [ ! -d "/tmp/noVNC" ]; then
        if [ -d "/tmp/novnc" ]; then
            ln -s /tmp/novnc /tmp/noVNC
        else
            git clone https://github.com/novnc/noVNC.git /tmp/noVNC > /tmp/novnc-clone.log 2>&1 || true
        fi
    fi

    if [ ! -f "/tmp/noVNC/vnc.html" ]; then
        echo "noVNC assets not found at /tmp/noVNC (vnc.html missing)."
        if [ -f "/tmp/novnc-clone.log" ]; then
            echo "Clone log (last 20 lines):"
            tail -n 20 /tmp/novnc-clone.log || true
        fi
        exit 1
    fi

    # Start Xvfb (use setsid so it survives shell exit)
    echo "Starting Xvfb on $DISPLAY_NUM..."
    setsid Xvfb "$DISPLAY_NUM" -screen 0 1024x768x24 +extension GLX +render -noreset > "$XVFB_LOG" 2>&1 &
    disown
    sleep 1

    if ! pgrep -x "Xvfb" > /dev/null; then
        echo "Failed to start Xvfb; check $XVFB_LOG"
        cat "$XVFB_LOG" 2>/dev/null || true
        exit 1
    fi
fi

# Ensure all dependent services are running (idempotent)
export DISPLAY="$DISPLAY_NUM"
start_openbox
start_x11vnc
start_websockify

ensure_novnc_ready || exit 1

echo ""
echo "X11 services running:"
echo "  Xvfb      – display $DISPLAY_NUM"
echo "  openbox   – window manager"
echo "  x11vnc    – VNC on port 5900"
echo "  websockify – noVNC on port 6080"
echo ""
echo "Access noVNC at: http://localhost:6080/vnc.html"
echo "Run GUI apps with: DISPLAY=:99 python main_interface.py"

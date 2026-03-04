#!/bin/bash

# Monitor PyInstaller builds in progress

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PYINSTALLER BUILD MONITOR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check active processes
echo "📊 Active Build Processes:"
ps aux | grep -E "pyinstaller|docker.*windows|python.*pip" | grep -v grep | while read line; do
    pid=$(echo "$line" | awk '{print $2}')
    cmd=$(echo "$line" | awk '{for(i=11;i<=NF;i++) printf "%s ", $i; print ""}' | cut -c1-70)
    mem=$(echo "$line" | awk '{print $6}' | numfmt --to=iec-i --suffix=B 2>/dev/null || echo "$line" | awk '{print $6}')
    cpu=$(echo "$line" | awk '{print $3}')
    echo "  PID $pid | CPU: ${cpu}% | Mem: ${mem} | $cmd"
done
echo ""

# Check build output directories
echo "📁 Build Output Status:"
if [ -d "build" ]; then
    echo "  ✓ ./build directory exists ($(du -sh build 2>/dev/null | cut -f1))"
else
    echo "  ✗ ./build directory not yet created"
fi

if [ -d "dist" ]; then
    size=$(du -sh dist 2>/dev/null | cut -f1)
    count=$(find dist -type f 2>/dev/null | wc -l)
    echo "  ✓ ./dist directory exists ($size, $count files)"
else
    echo "  ✗ ./dist directory not yet created"
fi

if [ -d ".venv/lib/python3.14/site-packages/PyInstaller" ]; then
    echo "  ✓ PyInstaller installed in .venv"
else
    echo "  ✗ PyInstaller not found in .venv"
fi
echo ""

# Check Docker status
echo "🐳 Docker Build Status:"
if docker ps 2>/dev/null | grep -q "pyinstaller-windows"; then
    echo "  ✓ Docker container running for Windows build"
    docker ps --no-trunc | grep pyinstaller-windows || true
else
    echo "  ✗ No Windows Docker container currently running"
fi
echo ""

# Show estimated time
echo "⏱️  Build Strategy:"
echo "  Windows build started via: ./build_windows_docker.sh --build-only"
echo "  Estimated stage: Requirements installation (pip install)"
echo "  Estimated remaining: 20-30 minutes"
echo ""
echo "💡 Next Steps:"
echo "  • Monitor build with: ./check_build.sh (this command)"
echo "  • Watch Docker logs: docker logs -f <container_id>"
echo "  • When done: ls -lh dist/Batch\\ File\\ Sender/"
echo "  • Run self-test: dist/Batch\\ File\\ Sender/Batch\\ File\\ Sender.exe --self-test"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

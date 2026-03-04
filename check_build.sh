#!/bin/bash
# Build status checker
cd /var/mnt/Disk2/projects/batch-file-processor

echo "=== BUILD STATUS CHECK ==="
echo "Time: $(date)"
echo ""

# Check if build is running
if pgrep -f "PyInstaller.*main_interface_native" > /dev/null 2>&1; then
    echo "Build Status: RUNNING"
    echo "Build log lines: $(wc -l < build.log 2>/dev/null || echo 'N/A')"
    echo "Last 5 log lines:"
    tail -5 build.log 2>/dev/null || echo "No log yet"
    exit 0
fi

# Check if executable exists
if [ -f "dist/Batch File Sender/Batch File Sender" ]; then
    echo "Build Status: SUCCESS ✓"
    ls -lh "dist/Batch File Sender/Batch File Sender"
    exit 0
fi

# Build must have failed
echo "Build Status: FAILED ✗"
echo "Last 30 log lines:"
tail -30 build.log 2>/dev/null || echo "No log available"
exit 1

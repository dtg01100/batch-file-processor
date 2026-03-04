#!/bin/bash

# Wait for Windows build to complete and show results

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

BUILD_TIMEOUT=${1:-3600}  # Default 60 minutes
CHECK_INTERVAL=30  # Check every 30 seconds

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║          WAITING FOR WINDOWS PYINSTALLER BUILD TO COMPLETE        ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Timeout: $BUILD_TIMEOUT seconds"
echo "Check interval: $CHECK_INTERVAL seconds"
echo ""

ELAPSED=0
while [ $ELAPSED -lt $BUILD_TIMEOUT ]; do
    # Check if Docker PyInstaller processes are running
    if ! ps aux | grep -q "pyinstaller.*main_interface_windows" | grep -v grep; then
        # Build appears complete
        echo ""
        echo "╔════════════════════════════════════════════════════════════════════╗"
        echo "║                    BUILD PROCESS COMPLETED                        ║"
        echo "╚════════════════════════════════════════════════════════════════════╝"
        echo ""
        
        # Check results
        if [ -f "dist/Batch File Sender/Batch File Sender.exe" ]; then
            echo "✅ SUCCESS: Windows executable created"
            echo ""
            echo "📊 Build Results:"
            ls -lh "dist/Batch File Sender/Batch File Sender.exe" | awk '{print "  File: " $9 " (" $5 ")"}'
            echo ""
            echo "🧪 Running Self-Test (optional)..."
            echo ""
            
            if command -v wine &> /dev/null; then
                wine "dist/Batch File Sender/Batch File Sender.exe" --self-test 2>&1 | head -20 || true
                echo ""
                echo "✓ Self-test execution complete (check output above)"
            else
                echo "Note: Wine not available for self-test. Executable created successfully though."
            fi
            
            echo ""
            echo "🎁 DELIVERABLE READY:"
            echo "   Path: $(pwd)/dist/Batch File Sender/Batch File Sender.exe"
            echo "   Size: $(du -h "dist/Batch File Sender/Batch File Sender.exe" | cut -f1)"
            echo ""
            echo "📋 Next Steps:"
            echo "   1. Copy dist/Batch File Sender/ to distribution location"
            echo "   2. Users can run without Python installed"
            echo "   3. Includes all PyQt6 libraries and dependencies"
            echo ""
            exit 0
            
        elif [ -d "dist/Batch File Sender" ] && [ -n "$(find dist/Batch\ File\ Sender -type f 2>/dev/null)" ]; then
            echo "⚠️  PARTIAL: Build directory created but executable missing"
            echo ""
            echo "📁 Build Contents:"
            ls -lh "dist/Batch File Sender/" 2>/dev/null | head -10
            echo ""
            echo "🔍 Checking for errors in build output..."
            if [ -f "build.log" ]; then
                tail -30 build.log | grep -i "error\|fatal\|fail" || echo "No obvious errors found in logs"
            fi
            exit 1
            
        else
            echo "❌ FAILED: No executable created"
            echo ""
            echo "🔍 Checking for Docker errors..."
            docker logs dreamy_visvesvaraya 2>&1 | tail -50 || echo "Could not retrieve Docker logs"
            exit 1
        fi
    fi
    
    # Show progress
    PCT=$((ELAPSED * 100 / BUILD_TIMEOUT))
    echo -ne "\r⏳ Waiting... ${ELAPSED}s elapsed (${PCT}%) | $(date '+%H:%M:%S')"
    
    sleep $CHECK_INTERVAL
    ELAPSED=$((ELAPSED + CHECK_INTERVAL))
done

echo ""
echo "❌ BUILD TIMEOUT: Exceeded $BUILD_TIMEOUT seconds"
echo ""
echo "🔍 Manual Check:"
echo "   Check container: docker logs dreamy_visvesvaraya"
echo "   Check files: ls -lh dist/"
echo "   Try rebuild: ./build_windows_docker.sh --rebuild"
exit 1

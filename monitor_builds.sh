#!/bin/bash
# Monitor both Linux and Windows builds

cd /var/mnt/Disk2/projects/batch-file-processor

echo "╔════════════════════════════════════════════════════╗"
echo "║    Monitoring Linux and Windows Builds             ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""

LINUX_DONE=0
WINDOWS_DONE=0
LINUX_SUCCESS=0
WINDOWS_SUCCESS=0

for i in {1..240}; do
  SLEEP_SECS=5
  
  echo -ne "\rMonitoring... ${i}0 seconds elapsed"
  
  # Check Linux build
  if [ $LINUX_DONE -eq 0 ]; then
    if [ -f "dist/Batch File Sender/Batch File Sender" ]; then
      LINUX_DONE=1
      echo ""
      echo "✓ Linux executable created"
      echo "  Running self-test..."
      if timeout 60 "dist/Batch File Sender/Batch File Sender" --self-test > /tmp/linux_test.log 2>&1; then
        LINUX_SUCCESS=1
        echo "  ✅ Linux self-test PASSED"
      else
        echo "  ⚠️  Linux self-test FAILED"
        tail -20 /tmp/linux_test.log
      fi
    fi
  fi
  
  # Check Windows build
  if [ $WINDOWS_DONE -eq 0 ]; then
    if [ -f "dist/Batch File Sender/Batch File Sender.exe" ]; then
      WINDOWS_DONE=1
      echo ""
      echo "✓ Windows executable created"
      echo "  Running self-test via Wine..."
      if timeout 60 wine "dist/Batch File Sender/Batch File Sender.exe" --self-test > /tmp/windows_test.log 2>&1; then
        WINDOWS_SUCCESS=1
        echo "  ✅ Windows self-test PASSED"
      else
        echo "  ⚠️  Windows self-test FAILED"
        tail -20 /tmp/windows_test.log | head -10
      fi
    fi
  fi
  
  # Exit if both done
  if [ $LINUX_DONE -eq 1 ] && [ $WINDOWS_DONE -eq 1 ]; then
    echo ""
    echo ""
    echo "╔════════════════════════════════════════════════════╗"
    echo "║  BUILD SUMMARY                                     ║"
    echo "╠════════════════════════════════════════════════════╣"
    
    if [ $LINUX_SUCCESS -eq 1 ]; then
      echo "║ ✅ Linux Build: SUCCESS                            ║"
    else
      echo "║ ⚠️ Linux Build: FAILED                              ║"
    fi
    
    if [ $WINDOWS_SUCCESS -eq 1 ]; then
      echo "║ ✅ Windows Build: SUCCESS                          ║"
    else
      echo "║ ⚠️ Windows Build: FAILED                            ║"
    fi
    
    echo "╚════════════════════════════════════════════════════╝"
    
    if [ $LINUX_SUCCESS -eq 1 ] && [ $WINDOWS_SUCCESS -eq 1 ]; then
      echo ""
      echo "🎉 ALL BUILDS SUCCESSFUL!"
      exit 0
    else
      echo ""
      echo "⚠️ Some builds failed. Check logs."
      exit 1
    fi
  fi
  
  sleep $SLEEP_SECS
done

echo ""
echo "Timeout: builds did not complete in 20 minutes"
exit 1

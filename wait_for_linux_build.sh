#!/bin/bash
# Wait for Linux build and test it

cd /var/mnt/Disk2/projects/batch-file-processor

echo "Waiting for Linux build to complete..."
for i in {1..240}; do # Wait up to 20 minutes
  if [ -f "dist/Batch File Sender/Batch File Sender" ]; then
    echo "✓ Build completed!"
    echo ""
    echo "Running self-test..."
    "dist/Batch File Sender/Batch File Sender" --self-test
    exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
      echo ""
      echo "✅ LINUX BUILD SUCCESS - SELF-TEST PASSED!"
      exit 0
    else
      echo ""
      echo "⚠️ Linux build created but self-test failed (exit code: $exit_code)"
      exit 1
    fi
  fi
  
  if [ $((i % 20)) -eq 0 ]; then
    echo "Still building... $(($i * 5)) seconds elapsed"
  fi
  
  sleep 5
done

# Timeout
echo "Build did not complete within 20 minutes"
tail -50 build.log
exit 1

#!/bin/bash
"""
Verify System Tools Script
Tests that all essential system tools are available and working
"""

echo "=== System Tools Verification ==="
echo "Testing essential system administration tools..."
echo

# Test process management tools
echo "✓ Process Management Tools:"
commands=("ps" "pgrep" "pkill" "kill" "killall" "htop" "top")
for cmd in "${commands[@]}"; do
    if command -v "$cmd" &> /dev/null; then
        echo "  ✓ $cmd - Available"
    else
        echo "  ✗ $cmd - Missing"
    fi
done
echo

# Test network tools  
echo "✓ Network Tools:"
net_commands=("netstat" "lsof" "ss")
for cmd in "${net_commands[@]}"; do
    if command -v "$cmd" &> /dev/null; then
        echo "  ✓ $cmd - Available"
    else
        echo "  ✗ $cmd - Missing"
    fi
done
echo

# Test file system tools
echo "✓ File System Tools:"
fs_commands=("tree" "unzip" "curl" "wget")
for cmd in "${fs_commands[@]}"; do
    if command -v "$cmd" &> /dev/null; then
        echo "  ✓ $cmd - Available"
    else
        echo "  ✗ $cmd - Missing"
    fi
done
echo

# Test specific functionality
echo "✓ Functionality Tests:"

# Test ps command
if ps aux > /dev/null 2>&1; then
    echo "  ✓ ps aux - Working"
else
    echo "  ✗ ps aux - Failed"
fi

# Test netstat command
if netstat -tuln > /dev/null 2>&1; then
    echo "  ✓ netstat -tuln - Working"
else
    echo "  ✗ netstat -tuln - Failed"
fi

# Test lsof command
if lsof -i > /dev/null 2>&1; then
    echo "  ✓ lsof -i - Working"
else
    echo "  ✗ lsof -i - Failed"
fi

echo
echo "=== Verification Complete ==="

# Show current running processes
echo
echo "Current processes:"
ps aux | head -10

echo
echo "Network connections:"
netstat -tuln 2>/dev/null | head -10 || ss -tuln | head -10
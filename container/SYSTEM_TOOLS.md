# System Tools Available in Docker Container

The Stock Analyst Docker containers now include essential system administration and process management tools:

## Process Management
- **ps** - Display running processes
- **pgrep** - Find process IDs by name
- **pkill** - Terminate processes by name  
- **kill** - Send signals to processes
- **killall** - Kill processes by name
- **htop** - Interactive process viewer
- **top** - Display and update sorted information about running processes

## Network Tools
- **netstat** - Display network connections and routing tables
- **lsof** - List open files and network connections
- **ss** - Socket statistics (modern netstat replacement)

## File System Tools
- **tree** - Display directory structure in tree format
- **unzip** - Extract ZIP archives
- **curl** - Transfer data from servers
- **wget** - Download files from web

## System Information
- **procps** package provides:
  - ps, top, vmstat, w, kill, free, slabtop, skill, snice, tload, uptime, watch, pidof
- **psmisc** package provides:
  - killall, fuser, pstree, peekfd

## Usage Examples

### Process Management
```bash
# List all processes
ps aux

# Find Flask processes
pgrep -f python.*app.py

# Kill webapp process
pkill -f "python.*app.py"

# Interactive process viewer
htop
```

### Network Monitoring
```bash
# Show listening ports
netstat -tuln

# Show what's using port 5000
lsof -i :5000

# Check network connections
ss -tuln
```

### Container Access
```bash
# Access container with full system tools
docker exec -it stockdev bash

# Run commands in container
docker exec stockdev ps aux
docker exec stockdev netstat -tuln
docker exec stockdev lsof -i :5000
```

## Webapp Management in Container

With these tools available, you can now:

1. **Monitor running processes** inside the container
2. **Kill specific processes** (like old Flask instances)  
3. **Check port usage** and network connections
4. **Debug process issues** effectively
5. **Manage webapp restarts** gracefully

The webapp_manager.py script will now work properly inside Docker containers since all required system tools are available.
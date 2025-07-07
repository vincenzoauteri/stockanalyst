#!/bin/bash
# Start both webapp and scheduler services
echo "Starting Stock Analyst services..."

# Start webapp manager in background
echo "Starting webapp manager..."
/app/webapp_manager.py start &

# Start scheduler in foreground (keeps container running)
echo "Starting scheduler..."
/app/scheduler.py start
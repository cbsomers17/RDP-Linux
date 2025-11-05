#!/bin/bash
# RDP-Linux Service Control Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/start.py"
PID_FILE="$SCRIPT_DIR/rdp_host.pid"
LOG_FILE="$SCRIPT_DIR/rdp_host.log"

start_server() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "Server is already running (PID: $PID)"
            return 1
        else
            echo "Removing stale PID file"
            rm -f "$PID_FILE"
        fi
    fi
    
    echo "Starting RDP-Linux server..."
    cd "$SCRIPT_DIR"
    python3 "$PYTHON_SCRIPT" > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    echo "Server started with PID: $(cat "$PID_FILE")"
    echo "Log file: $LOG_FILE"
}

stop_server() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "Stopping server (PID: $PID)..."
            kill "$PID"
            sleep 2
            if ps -p "$PID" > /dev/null 2>&1; then
                echo "Force killing server..."
                kill -9 "$PID"
            fi
            rm -f "$PID_FILE"
            echo "Server stopped"
        else
            echo "Server is not running"
            rm -f "$PID_FILE"
        fi
    else
        echo "Server is not running (no PID file found)"
    fi
}

status_server() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "Server is running (PID: $PID)"
            echo "Listening on port 3389"
            return 0
        else
            echo "Server is not running (stale PID file)"
            return 1
        fi
    else
        echo "Server is not running"
        return 1
    fi
}

restart_server() {
    stop_server
    sleep 2
    start_server
}

case "$1" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    restart)
        restart_server
        ;;
    status)
        status_server
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        echo ""
        echo "  start   - Start the RDP-Linux server"
        echo "  stop    - Stop the RDP-Linux server"
        echo "  restart - Restart the RDP-Linux server"
        echo "  status  - Check server status"
        exit 1
        ;;
esac

exit $?
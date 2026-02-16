#!/usr/bin/env bash
set -e

# Helper script to run browser tests with automatic server management
# Starts server, runs tests, stops server on exit

PORT=8000
SERVER_PID=""
SERVER_BIN=""

cleanup() {
    if [[ -n "$SERVER_PID" ]]; then
        echo "Stopping server (PID: $SERVER_PID)..."
        kill "$SERVER_PID" 2>/dev/null || true
    fi
    if [[ -n "$SERVER_BIN" ]]; then
        rm -f "$SERVER_BIN"
    fi
}

trap cleanup EXIT INT TERM

# Check if port is already in use
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "Server already running on port $PORT, using existing instance"
    uv run --with pytest --with pytest-playwright pytest test_browser.py -v "$@"
    exit $?
fi

# Build site
echo "Building site..."
mise run build

# Build server binary
echo "Compiling server..."
SERVER_BIN=$(mktemp)
go build -o "$SERVER_BIN" ./goServe/main.go

# Start server in background
echo "Starting server on port $PORT..."
"$SERVER_BIN" -port "$PORT" -directory ./public &
SERVER_PID=$!

# Wait for server to be ready (timeout: 3s)
echo "Waiting for server to start..."
for i in {1..6}; do
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
        echo "Server process died unexpectedly"
        exit 1
    fi
    if curl -s --max-time 1 http://localhost:$PORT >/dev/null 2>&1; then
        echo "Server ready"
        break
    fi
    if [ $i -eq 6 ]; then
        echo "Server failed to start within 3s"
        exit 1
    fi
    sleep 0.5
done

# Run tests
echo "Running browser tests..."
uv run --with pytest --with pytest-playwright pytest test_browser.py -v "$@"
TEST_EXIT_CODE=$?

exit $TEST_EXIT_CODE

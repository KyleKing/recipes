#!/usr/bin/env bash
set -e

# Helper script to run browser tests with automatic server management
# Starts server, runs tests, stops server on exit

PORT=8000
SERVER_PID=""

cleanup() {
    if [[ -n "$SERVER_PID" ]]; then
        echo "Stopping server (PID: $SERVER_PID)..."
        kill "$SERVER_PID" 2>/dev/null || true
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

# Start server in background
echo "Starting server on port $PORT..."
go run ./goServe/main.go --port=$PORT --directory=./public &
SERVER_PID=$!

# Wait for server to be ready
echo "Waiting for server to start..."
for i in {1..30}; do
    if curl -s http://localhost:$PORT >/dev/null 2>&1; then
        echo "Server ready"
        break
    fi
    sleep 0.5
    if [ $i -eq 30 ]; then
        echo "Server failed to start"
        exit 1
    fi
done

# Run tests
echo "Running browser tests..."
uv run --with pytest --with pytest-playwright pytest test_browser.py -v "$@"
TEST_EXIT_CODE=$?

exit $TEST_EXIT_CODE

#!/bin/bash
# Setup script for go-spacy C++ wrapper library
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
LIB_DIR="$PROJECT_ROOT/lib"
BUILD_DIR="/tmp/go-spacy-build"

echo "Setting up go-spacy C++ wrapper..."

# Create lib directory
mkdir -p "$LIB_DIR"

# Check if library already exists
if [ -f "$LIB_DIR/libspacy_wrapper.dylib" ] || [ -f "$LIB_DIR/libspacy_wrapper.so" ]; then
    echo "✓ go-spacy library already exists"
    exit 0
fi

# Copy go-spacy source to temp directory
echo "Copying go-spacy source..."
GOSPACY_PATH=$(go list -m -f '{{.Dir}}' github.com/am-sokolov/go-spacy)
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
cp -r "$GOSPACY_PATH"/* "$BUILD_DIR/"
chmod -R u+w "$BUILD_DIR"

# Build the C++ wrapper
echo "Building C++ wrapper..."
cd "$BUILD_DIR"

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    SHARED_EXT="dylib"
    PYTHON_LIB_PATH=$(python3-config --prefix)/lib
else
    SHARED_EXT="so"
    PYTHON_LIB_PATH=$(python3-config --prefix)/lib
fi

# Create build directories
mkdir -p build lib

# Compile
echo "Compiling..."
c++ -Wall -Wextra -fPIC -std=c++17 -Iinclude -O3 -DNDEBUG \
    $(python3-config --cflags) \
    -c cpp/spacy_wrapper.cpp -o build/spacy_wrapper.o

# Link
echo "Linking..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    c++ -shared -install_name @rpath/libspacy_wrapper.dylib \
        -o lib/libspacy_wrapper.$SHARED_EXT \
        build/spacy_wrapper.o \
        -L"$PYTHON_LIB_PATH" \
        $(python3-config --ldflags)
else
    c++ -shared -Wl,-soname,libspacy_wrapper.$SHARED_EXT \
        -o lib/libspacy_wrapper.$SHARED_EXT \
        build/spacy_wrapper.o \
        -L"$PYTHON_LIB_PATH" \
        $(python3-config --ldflags)
fi

# Copy to project lib directory
echo "Installing library..."
cp lib/libspacy_wrapper.$SHARED_EXT "$LIB_DIR/"

echo "✓ go-spacy library installed to $LIB_DIR"
echo ""
echo "To use in your shell session, export these variables:"
echo "  export CGO_LDFLAGS=\"-L$LIB_DIR -L$PYTHON_LIB_PATH -Wl,-rpath,$LIB_DIR -Wl,-rpath,$PYTHON_LIB_PATH\""
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "  export DYLD_LIBRARY_PATH=\"$LIB_DIR:$PYTHON_LIB_PATH:\$DYLD_LIBRARY_PATH\""
else
    echo "  export LD_LIBRARY_PATH=\"$LIB_DIR:$PYTHON_LIB_PATH:\$LD_LIBRARY_PATH\""
fi

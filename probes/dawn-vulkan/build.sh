#!/bin/sh
# Scaffold: configure Dawn Vulkan-only, then build adapter_device against it.
# Populate third_party first: python3 tools/fetch_dawn_dependencies.py -d "$DAWN" -s
set -e
DAWN_SRC=${DAWN_SRC:?}
BUILD=${BUILD:-/tmp/dawn-vulkan-build}
cmake -S "$DAWN_SRC" -B "$BUILD" \
  -DCMAKE_BUILD_TYPE=Release \
  -DDAWN_FETCH_DEPENDENCIES=OFF \
  -DDAWN_ENABLE_VULKAN=ON \
  -DDAWN_ENABLE_D3D11=OFF -DDAWN_ENABLE_D3D12=OFF \
  -DDAWN_ENABLE_METAL=OFF -DDAWN_ENABLE_NULL=OFF \
  -DDAWN_ENABLE_DESKTOP_GL=OFF -DDAWN_ENABLE_OPENGLES=OFF \
  -DDAWN_USE_X11=OFF -DDAWN_USE_WAYLAND=OFF -DDAWN_USE_GLFW=OFF \
  -DDAWN_BUILD_SAMPLES=OFF -DDAWN_BUILD_TESTS=OFF \
  -DDAWN_BUILD_PROTOBUF=OFF -DTINT_BUILD_TESTS=OFF \
  -DTINT_BUILD_CMD_TOOLS=OFF
cmake --build "$BUILD" -j"${MAKE_JOBS:-8}"
# Link adapter_device.cpp against dawn_native / dawn_proc from $BUILD (paths vary by Dawn version).

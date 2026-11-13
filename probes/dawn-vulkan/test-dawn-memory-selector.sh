#!/bin/sh
# SPDX-License-Identifier: MIT
# Origin: EmberBSD contributors (AI-assisted).
# Run against the prepared (patched) pinned Dawn source and native Ports SDK.
set -eu
if [ "$#" -ne 2 ]; then
    echo "usage: $0 PREPARED_DAWN_ROOT NATIVE_SDK_PREFIX" >&2; exit 2
fi
src=$1
sdk=$2
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/dawn-selector.XXXXXX")
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
mkdir -p "$tmp/src/dawn/common" "$tmp/src/dawn/native/vulkan" "$tmp/src/utils"
cat > "$tmp/src/dawn/common/vulkan_platform.h" <<'END'
#include <vulkan/vulkan.h>
END
cat > "$tmp/src/dawn/native/vulkan/VulkanInfo.h" <<'END'
#include <vector>
#include <vulkan/vulkan.h>
namespace dawn::native::vulkan { struct VulkanDeviceInfo { std::vector<VkMemoryType> memoryTypes; std::vector<VkMemoryHeap> memoryHeaps; }; }
END
cat > "$tmp/src/utils/numeric.h" <<'END'
namespace dawn { template <typename To, typename From> To checked_cast(From x) { return static_cast<To>(x); } }
END
"$sdk/bin/clang++" -std=c++20 -I"$tmp" -I"$src" -I"$src/include" -I"$sdk/include" \
    "$here/test-dawn-memory-selector.cpp" "$src/src/dawn/native/vulkan/MemoryTypeSelector.cpp" -o "$tmp/test"
"$tmp/test"

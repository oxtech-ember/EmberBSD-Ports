#!/bin/sh
# SPDX-License-Identifier: MIT
# NetBSD adaptations for the ORT-pinned Dawn tree (Vulkan desktop).
# Treat NetBSD as Linux/POSIX for Vulkan loader + SystemUtils, but do not
# claim LINUX_DESKTOP and do not compile Linux-only DMA-BUF / OpaqueFD /
# semaphore-FD importers (headers gate those on __linux__).
set -eu
root=$1

platform=$root/src/utils/platform.h
if ! grep -q '__NetBSD__' "$platform"; then
	tmp=$platform.emberbsd
	awk '
	  /#elif defined\(__EMSCRIPTEN__\)/ { seen=1 }
	  seen && /^#else$/ && !done {
	    print "#elif defined(__NetBSD__) || defined(__FreeBSD__) || defined(__OpenBSD__) || defined(__DragonFly__)"
	    print "// EmberBSD/NetBSD: POSIX + Linux-like for Vulkan loader; no LINUX_DESKTOP."
	    print "#define DAWN_PLATFORM_IS_LINUX 1"
	    print "#define DAWN_PLATFORM_IS_POSIX 1"
	    print ""
	    done=1
	  }
	  { print }
	' "$platform" > "$tmp"
	mv "$tmp" "$platform"
fi

drm=$root/src/dawn/common/DRMUtils.cpp
if [ -f "$drm" ] && ! grep -q 'major()/minor() on NetBSD' "$drm"; then
	tmp=$drm.emberbsd
	if grep -q 'defined(__linux__)' "$drm" && grep -q 'sys/sysmacros.h' "$drm"; then
		# Already gated for Linux; add NetBSD types include in the else branch.
		awk '
		  /#if defined\(__linux__\)/ { print; inlinux=1; next }
		  inlinux && /#include <sys\/sysmacros.h>/ { print; next }
		  inlinux && /^#endif$/ {
		    print "#else"
		    print "#include <sys/types.h> /* major()/minor() on NetBSD */"
		    print "#endif"
		    inlinux=0
		    next
		  }
		  { print }
		' "$drm" > "$tmp"
	else
		awk '
		  /#include <sys\/sysmacros.h>/ {
		    print "#if defined(__linux__)"
		    print "#include <sys/sysmacros.h>"
		    print "#else"
		    print "#include <sys/types.h> /* major()/minor() on NetBSD */"
		    print "#endif"
		    next
		  }
		  { print }
		' "$drm" > "$tmp"
	fi
	mv "$tmp" "$drm"
fi

rdc=$root/third_party/renderdoc/renderdoc/api/app/renderdoc_app.h
if [ -f "$rdc" ] && ! grep -q '__NetBSD__' "$rdc"; then
	tmp=$rdc.emberbsd
	sed -e 's/defined(__FreeBSD__) || defined(__sun__)/defined(__FreeBSD__) || defined(__NetBSD__) || defined(__DragonFly__) || defined(__sun__)/' \
	    "$rdc" > "$tmp"
	mv "$tmp" "$rdc"
fi

native=$root/src/dawn/native/CMakeLists.txt
if [ -f "$native" ] && grep -q 'elseif (UNIX AND NOT APPLE)' "$native"; then
	tmp=$native.emberbsd
	# Gate Linux-only DMA-BUF / OpaqueFD importers.
	awk '
	  /elseif \(UNIX AND NOT APPLE\)/ && !done {
	    print "    elseif (CMAKE_SYSTEM_NAME STREQUAL \"Linux\")"
	    done=1
	    next
	  }
	  { print }
	' "$native" > "$tmp"
	mv "$tmp" "$native"
fi

# VulkanBackend.h declares FD image types under defined(__linux__), while the
# .cpp used DAWN_PLATFORM_IS(LINUX). Align the .cpp with the public header.
vkb=$root/src/dawn/native/vulkan/VulkanBackend.cpp
if [ -f "$vkb" ] && grep -q 'DAWN_PLATFORM_IS(LINUX)' "$vkb"; then
	tmp=$vkb.emberbsd
	sed -e 's/DAWN_PLATFORM_IS(LINUX)/defined(__linux__)/g' \
	    -e 's/DAWN_PLATFORM_IS(ANDROID) || defined(__linux__)/DAWN_PLATFORM_IS(ANDROID) || defined(__linux__)/g' \
	    "$vkb" > "$tmp"
	# Restore ANDROID-only blocks that sed may have touched incorrectly:
	# the file uses DAWN_PLATFORM_IS(ANDROID) separately; only LINUX→__linux__.
	mv "$tmp" "$vkb"
fi

# Semaphore FD importer is only built on Linux; do not reference CreateFDService.
sem=$root/src/dawn/native/vulkan/external_semaphore/SemaphoreService.cpp
if [ -f "$sem" ] && grep -q 'DAWN_PLATFORM_IS(LINUX)' "$sem"; then
	tmp=$sem.emberbsd
	sed -e 's/DAWN_PLATFORM_IS(LINUX)/defined(__linux__)/g' "$sem" > "$tmp"
	mv "$tmp" "$sem"
fi

# The Raven2 RADV adapter on NetBSD cannot safely read directly host-mapped
# device-local storage after larger uploads. Hide both optional map extensions;
# ordinary staging copies remain available. This is not a GPUVM fix.
physical=$root/src/dawn/native/vulkan/PhysicalDeviceVk.cpp
original='    if (!gpu_info::IsNvidia(GetVendorId()) && SupportsBufferMapExtendedUsages(mDeviceInfo)) {'
patched='    if (!netbsdRaven2MapStorageBroken &&'
continuation='        !gpu_info::IsNvidia(GetVendorId()) && SupportsBufferMapExtendedUsages(mDeviceInfo)) {'
marker='    // NetBSD RADV Raven2: direct host-mapped storage reads are unreliable.'
if [ "$(grep -Fxc "$marker" "$physical" || :)" -eq 1 ]; then
	for line in "$patched" "$continuation" \
	    '    const bool netbsdRaven2MapStorageBroken =' \
	    '        IsAmdMesa() && GetVendorId() == 0x1002 && GetDeviceId() == 0x15d8;' \
	    '    constexpr bool netbsdRaven2MapStorageBroken = false;'; do
		[ "$(grep -Fxc "$line" "$physical" || :)" -eq 1 ] || {
			echo "Dawn Raven2 feature guard is incomplete" >&2; exit 1;
		}
	done
else
	[ "$(grep -Fxc "$original" "$physical" || :)" -eq 1 ] || {
		echo "Dawn BufferMapExtendedUsages preimage changed" >&2; exit 1;
	}
	# Match the complete pinned feature block, not just its condition.
	awk -v original="$original" '
	  $0 == original {
	    if (getline a <= 0 || getline b <= 0 || getline c <= 0 ||
	        getline d <= 0 || getline e <= 0) exit 1
	    if (a != "        EnableFeature(Feature::BufferMapExtendedUsages);" ||
	        b != "        // Now `kMapExtendedUsageMemoryPropertyFlags` contains exactly the flags that are required" ||
	        c != "        // for `BufferMapWriteExtendedUsages`." ||
	        d != "        EnableFeature(Feature::BufferMapWriteExtendedUsages);" || e != "    }") exit 1
	    found++
	  }
	  END { if (found != 1) exit 1 }
	' "$physical" || { echo "Dawn mapped-feature block changed" >&2; exit 1; }
	tmp=$physical.emberbsd
	awk -v original="$original" -v patched="$patched" -v continuation="$continuation" -v marker="$marker" '
	  $0 == original {
	    print marker
	    print "#if defined(__NetBSD__)"
	    print "    const bool netbsdRaven2MapStorageBroken ="
	    print "        IsAmdMesa() && GetVendorId() == 0x1002 && GetDeviceId() == 0x15d8;"
	    print "#else"
	    print "    constexpr bool netbsdRaven2MapStorageBroken = false;"
	    print "#endif"
	    print patched
	    print continuation
	    next
	  }
	  { print }
	' "$physical" > "$tmp"
	mv "$tmp" "$physical"
fi

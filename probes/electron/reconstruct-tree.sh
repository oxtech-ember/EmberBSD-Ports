#!/bin/sh
# EmberBSD E12: reconstruct the cross Chromium tree from distfiles.
# Reproduces the full fix set (see Ports probes/electron + memory e12-e16-quintet-port).
# Source tree: /Volumes/BigData/EmberBSD/work/e12-chromium (agent-local source copy;
# shared build dirs per AGENTS.md live elsewhere).
set -eu

BIG=/Volumes/BigData/EmberBSD
DIST=$BIG/distfiles/e12-electron
TREE=$BIG/work/e12-chromium
NB=$BIG/work/emberbsd-ports/upstream/pkgsrc/www/chromium
HOSTPREFIX=/private/tmp/ember-common-stack/host
SYSROOT=/private/tmp/ember-common-stack/sysroot
CROSSTOOLS=$BIG/work/ember-gcc16-toolchain/bin
SDK=$(xcrun --show-sdk-path)
XC=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr

echo "== extract =="
rm -rf "$TREE"
mkdir -p "$TREE"
cd "$TREE"
COPYFILE_DISABLE=1 tar --no-xattrs -xf "$DIST/chromium-152.0.7977.82.tar.xz" --strip-components=1

echo "== git baseline =="
git init -q
git add -A
git -c user.name=ember-e12 -c user.email=e12@ember commit -qm "Chromium 152.0.7977.82 official tarball (baseline)"

echo "== chromium-nb patchset =="
fail=0
for p in "$NB"/patches/patch-*; do
  patch --forward --no-backup-if-mismatch -p0 -i "$p" >/dev/null 2>&1 || fail=$((fail+1))
done
rm -f Oops.rej
echo "nb patch failures (expect 2 rollup-napi N/A): $fail"
git add -A
git -c user.name=ember-e12 -c user.email=e12 commit -qm "Apply chromium-nb patchset v151.1 (two rollup-napi patches N/A on the official tarball)"

echo "== chromium-nb overlay files =="
mkdir -p /tmp/nb-ol && rm -rf /tmp/nb-ol/*
tar -xzf "$DIST/chromium-nb-v151.1.tar.gz" -C /tmp/nb-ol
cd /tmp/nb-ol/chromium-nb-*
tar -cf - $(find . -type f -not -path './patches/*' -not -name '.gitignore' | sed 's|^\./||') | (cd "$TREE" && tar -xf -)
cd "$TREE"

echo "== cross adaptations =="
python3 - << 'PYEOF'
import re

def edit(path, old, new, count=1):
    s = open(path).read()
    if new in s and old not in s:
        return  # already applied
    assert old in s, f"anchor missing in {path}: {old[:60]!r}"
    s = s.replace(old, new, count)
    open(path, 'w').write(s)

# 1. gcc_arm64 toolchain
edit('build/toolchain/netbsd/BUILD.gn', '''clang_toolchain("clang_arm64") {
  toolchain_args = {
    current_cpu = "arm64"
    current_os = "netbsd"
  }
}
''', '''clang_toolchain("clang_arm64") {
  toolchain_args = {
    current_cpu = "arm64"
    current_os = "netbsd"
  }
}

# EmberBSD cross profile (E12): GCC16 cross toolchain from the build host.
gcc_toolchain("gcc_arm64") {
  cc = "aarch64--netbsd-gcc"
  cxx = "aarch64--netbsd-g++"

  readelf = "aarch64--netbsd-readelf"
  nm = "aarch64--netbsd-nm"
  ar = "aarch64--netbsd-ar"
  ld = cxx

  toolchain_args = {
    current_cpu = "arm64"
    current_os = "netbsd"
    is_clang = false
  }
}
''')

# 2. SUBST equivalents (target prefix)
import os
files = """base/base_paths_posix.cc base/process/process_handle_openbsd.cc build/linux/strip_binary.gni
build/rust/rust_bindgen.gni chrome/common/chrome_paths.cc components/policy/core/common/policy_paths.cc
sandbox/policy/openbsd/sandbox_openbsd.cc services/device/hid/hid_service_freebsd.cc
services/device/time_zone_monitor/time_zone_monitor_linux.cc third_party/dawn/tools/generate-sources-gn.py
third_party/pdfium/core/fxge/linux/fx_linux_impl.cpp third_party/perfetto/src/base/utils.cc
third_party/test_fonts/fontconfig/BUILD.gn third_party/vulkan-loader/src/BUILD.gn
third_party/wayland/BUILD.gn v8/tools/run-paxctl.py""".split()
for f in files:
    if os.path.exists(f):
        s = open(f).read()
        for a, b in [('@PREFIX@','/usr/pkg'), ('@PKG_SYSCONFBASE@','/etc'), ('@VARBASE@','/var'),
                     ('@QTDIR@','/usr/pkg/qt6'), ('@X11BASE@','/usr/X11R7'),
                     ('@PYTHONBIN@','/opt/homebrew/bin/python3')]:
            s = s.replace(a, b)
        open(f, 'w').write(s)

# host-prefix tool paths
edit('build/config/rust.gni', '@PREFIX@', '/private/tmp/ember-common-stack/host')
s = open('build/config/rust.gni').read().replace('@PYTHONBIN@','/opt/homebrew/bin/python3')
open('build/config/rust.gni','w').write(s)
edit('build/rust/rust_bindgen.gni', '_bindgen_path = "/usr/pkg/bin/bindgen"',
     '_bindgen_path = "/private/tmp/ember-common-stack/host/bin/bindgen"')
edit('build/rust/rust_bindgen_generator.gni', '_bindgen_path = "/usr/pkg/bin/bindgen"',
     '_bindgen_path = "/private/tmp/ember-common-stack/host/bin/bindgen"')
edit('build/rust/rust_bindgen_generator.gni', '_rustfmt_path = "/usr/pkg/bin/rustfmt"',
     '_rustfmt_path = "/private/tmp/ember-common-stack/host/bin/rustfmt"')
edit('build/rust/rust_bindgen_generator.gni', '_libclang_path = "/usr/pkg"',
     '_libclang_path = "/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr"')

# 3. wayland host-scanner assert
edit('third_party/wayland/BUILD.gn', 'assert(is_linux || is_chromeos || target_os == "linux")',
     '''# EmberBSD cross profile (E12): the host toolchain (macOS) builds the host
# wayland-scanner while the target is NetBSD; accept that host context.
assert(is_linux || is_chromeos || target_os == "linux" || current_os == "mac")''')

# 4. sysroot arg for module scan
edit('build/config/sysroot.gni', '''  # The path of the sysroot for the current toolchain. If empty, default
  # sysroot is used.
  sysroot = ""
}''', '''  # The path of the sysroot for the current toolchain. If empty, default
  # sysroot is used.
  sysroot = ""

  # EmberBSD cross profile (E12): sysroot used for header scans (unified
  # modules) when the default sysroot is empty in a cross build.
  emberbsd_target_sysroot = ""
}''')
edit('build/modules/BUILD.gn', '''  if (root_include_dir != "") {
    system_headers += expand_directory("${sysroot}/${root_include_dir}", true)
  }''', '''  if (root_include_dir != "") {
    # EmberBSD cross profile (E12): when no sysroot is set (native NetBSD has
    # /usr/include on the host), scan the declared target sysroot instead.
    _scan_root = sysroot
    if (_scan_root == "") {
      _scan_root = emberbsd_target_sysroot
    }
    system_headers += expand_directory("${_scan_root}/${root_include_dir}", true)
  }''')

# 5. mac runtime_library guard + darwin source
edit('build/config/mac/BUILD.gn', '''config("runtime_library") {
  common_flags = [
    "-isysroot",
    rebase_path(sysroot, root_build_dir),
    "-mmacos-version-min=$mac_deployment_target",
  ]

  asmflags = common_flags
  cflags = common_flags
  ldflags = common_flags

  # TODO(https://crbug.com/442128549): see if we can convince upstream rust to
  # add an -isysroot flag instead.
  rustenv = [ "SDKROOT=" + rebase_path(sysroot, root_build_dir) ]
}''', '''config("runtime_library") {
  # EmberBSD cross profile (E12): mac configs can be evaluated in the
  # NetBSD default-toolchain context through ($default_toolchain) deps of
  # host tools; apply mac SDK flags only in a real mac context.
  common_flags = []
  if (current_os == "mac") {
    common_flags = [
      "-isysroot",
      rebase_path(sysroot, root_build_dir),
      "-mmacos-version-min=$mac_deployment_target",

      # EmberBSD cross profile (E12): bundled libc++ bsd_like support calls
      # asprintf, which _XOPEN_SOURCE alone hides on darwin.
      "-D_DARWIN_C_SOURCE",
    ]
  }

  asmflags = common_flags
  cflags = common_flags
  ldflags = common_flags

  # TODO(https://crbug.com/442128549): see if we can convince upstream rust to
  # add an -isysroot flag instead.
  if (current_os == "mac") {
    rustenv = [ "SDKROOT=" + rebase_path(sysroot, root_build_dir) ]
  }
}''')

# 6. is_clang=true pins for mac host toolchains
edit('build/toolchain/mac/BUILD.gn', '''    toolchain_args = {
      forward_variables_from(invoker.toolchain_args, "*")
      current_os = "mac"
      if (target_os == "ios") {''', '''    toolchain_args = {
      forward_variables_from(invoker.toolchain_args, "*")
      current_os = "mac"

      # EmberBSD cross profile (E12): the target build sets is_clang=false
      # globally for its GCC toolchain; the file-scope args override would
      # leak into this macOS host toolchain. The host stays Clang.
      is_clang = true

      if (target_os == "ios") {''')
edit('build/toolchain/apple/toolchain.gni', '''    toolchain_args = {
      # Populate toolchain args from the invoker.
      forward_variables_from(invoker.toolchain_args, "*")
      toolchain_for_rust_host_build_tools = true

      # The host build tools are static release builds to make the Chromium
      # build faster. They do not need PGO etc, so no official builds.''', '''    toolchain_args = {
      # Populate toolchain args from the invoker.
      forward_variables_from(invoker.toolchain_args, "*")
      toolchain_for_rust_host_build_tools = true

      # EmberBSD cross profile (E12): the target build sets is_clang=false
      # globally for its GCC toolchain; the file-scope args override would
      # leak into this macOS host toolchain and switch its libc++ link
      # logic to GCC mode (missing libgcc_s on darwin). Keep it Clang.
      is_clang = true

      # The host build tools are static release builds to make the Chromium
      # build faster. They do not need PGO etc, so no official builds.''')

# 7. Xcode clang resource version
edit('build/toolchain/toolchain.gni', '''declare_args() {
  if (llvm_force_head_revision) {
    clang_version = "24"
  } else {''', '''declare_args() {
  if (llvm_force_head_revision) {
    clang_version = "24"
  } else if (is_apple && host_os == "mac") {
    # EmberBSD cross profile (E12): the macOS host toolchain uses the
    # system Xcode clang, whose resource directory carries its own
    # version (for example clang/21), not the pinned Chromium LLVM.
    clang_version = "21"
  } else {''')

# 8. compiler config: gnu++ dialect (mac-host else branch)
edit('build/config/compiler/BUILD.gn', '''    if (use_cxx23) {
      cflags_cc += [ "-std=c++23" ]
    } else {
      cflags_cc += [ "-std=c++20" ]
    }
  }''', '''    # EmberBSD cross profile (E12), mirrors pkgsrc BUILDLINK_TRANSFORM
    # (-std=c++20 -> -std=gnu++20): BSD asprintf and friends stay visible
    # in the bundled libc++ bsd_like locale support on every host.
    if (use_cxx23) {
      cflags_cc += [ "-std=gnu++23" ]
    } else {
      cflags_cc += [ "-std=gnu++20" ]
    }
  }''')

# 9. compiler config: GCC budgets + pkg includes in the is_linux branch (netbsd path)
edit('build/config/compiler/BUILD.gn', '''    cflags_c += [ "-std=${standard_prefix}11" ]
    if (use_cxx23) {
      cflags_cc += [ "-std=${standard_prefix}++23" ]
    } else {
      cflags_cc += [ "-std=${standard_prefix}++20" ]
    }
  } else if (is_win) {''', '''    cflags_c += [ "-std=${standard_prefix}11" ]
    if (use_cxx23) {
      cflags_cc += [ "-std=${standard_prefix}++23" ]
    } else {
      cflags_cc += [ "-std=${standard_prefix}++20" ]
    }

    # EmberBSD cross profile (E12): the BSD targets land in this branch
    # (is_linux includes netbsd via the chromium-nb build config).
    # GCC enforces the single-call inline budget for always_inline lambdas
    # stricter than Chromium's Clang; raise the budgets for GCC builds.
    if (!is_clang) {
      cflags += [
        "--param=max-inline-insns-single=10000",
        "--param=max-inline-insns-auto=10000",
        "--param=large-function-insns=100000",
        "--param=large-function-growth=1000",
        "--param=inline-unit-growth=1000",
      ]
    }

    # EmberBSD cross profile (E12): system headers of the pkg prefix from
    # the cross sysroot (glib and friends used by the message loop and UI
    # stacks). Native NetBSD resolves them through pkgsrc buildlinks.
    if (is_bsd && host_os == "mac") {
      cflags += [
        "-isystem/private/tmp/ember-common-stack/sysroot/usr/pkg/include",
        "-isystem/private/tmp/ember-common-stack/sysroot/usr/pkg/include/glib-2.0",
        "-isystem/private/tmp/ember-common-stack/sysroot/usr/pkg/lib/glib-2.0/include",
        "-isystem/private/tmp/ember-common-stack/sysroot/usr/pkg/include/libepoll-shim",
      ]
    }
  } else if (is_win) {''')

# 10. apple-clang flag guards
edit('build/config/compiler/BUILD.gn', '''    if (!is_wasm) {
      if (!is_win && !is_bsd) {
        cflags += [ "-fdiagnostics-show-inlining-chain" ]
      } else if (!is_bsd) {
        # Combine after https://github.com/llvm/llvm-project/pull/192241
        cflags += [ "/clang:-fdiagnostics-show-inlining-chain" ]
      }
    }''', '''    if (!is_wasm) {
      # EmberBSD cross profile (E12): Apple's system clang does not know
      # this flag; it exists only in Chromium's pinned LLVM.
      _apple_system_clang = is_apple && use_system_xcode
      if (!is_win && !is_bsd && !_apple_system_clang) {
        cflags += [ "-fdiagnostics-show-inlining-chain" ]
      } else if (!is_bsd && !_apple_system_clang) {
        # Combine after https://github.com/llvm/llvm-project/pull/192241
        cflags += [ "/clang:-fdiagnostics-show-inlining-chain" ]
      }
    }''')
edit('build/config/compiler/BUILD.gn', '''    # The performance improvement does not seem worth the risk. See
    # https://crbug.com/484082200 for background and https://crrev.com/c/7593035
    # for discussion.
    if (!is_wasm) {
      cflags += [ "-fno-lifetime-dse" ]
    }''', '''    # The performance improvement does not seem worth the risk. See
    # https://crbug.com/484082200 for background and https://crrev.com/c/7593035
    # for discussion.
    # EmberBSD cross profile (E12): Apple's system clang does not support
    # this flag.
    if (!is_wasm && !(is_apple && use_system_xcode)) {
      cflags += [ "-fno-lifetime-dse" ]
    }''')
edit('build/config/sanitizers/sanitizers.gni', '''    if (_condition && !is_ubsan && is_clang) {
      cflags = [
        "-fsanitize=${invoker.sanitizer}",
        "-fsanitize-trap=${invoker.sanitizer}",

        # Prevents `__has_feature(undefined_behavior_sanitizer)`
        # from evaluating true. Configs defined here are intended
        # to be usable even in release builds, i.e. as widely as possible.
        # It's important not to have full-on UBSan workarounds activate
        # just because we built support for a specific sanitizer.
        "-fsanitize-ignore-for-ubsan-feature=${invoker.sanitizer}",
      ]
      if (defined(invoker.cflags)) {
        cflags += invoker.cflags
      }
    }''', '''    if (_condition && !is_ubsan && is_clang) {
      cflags = [
        "-fsanitize=${invoker.sanitizer}",
        "-fsanitize-trap=${invoker.sanitizer}",
      ]

      # Prevents `__has_feature(undefined_behavior_sanitizer)`
      # from evaluating true. Configs defined here are intended
      # to be usable even in release builds, i.e. as widely as possible.
      # It's important not to have full-on UBSan workarounds activate
      # just because we built support for a specific sanitizer.
      # EmberBSD cross profile (E12): Apple's system clang does not
      # support the ignore flag; skip it there.
      if (!(is_apple && use_system_xcode)) {
        cflags +=
            [ "-fsanitize-ignore-for-ubsan-feature=${invoker.sanitizer}" ]
      }
      if (defined(invoker.cflags)) {
        cflags += invoker.cflags
      }
    }''')

# 11. rust std libs only in matching toolchain context
edit('build/rust/std/BUILD.gn', '''    } else if (target_os == "freebsd") {
      libs = [
        "execinfo",
        "pthread",
      ]
    } else if (target_os == "netbsd") {
      libs = [
        "rt",
        "pthread",
      ]
    } else if (is_ios) {''', '''    } else if (target_os == "freebsd" && current_os == "freebsd") {
      libs = [
        "execinfo",
        "pthread",
      ]
    } else if (target_os == "netbsd" && current_os == "netbsd") {
      # EmberBSD cross profile (E12): the host build-tools toolchain also
      # evaluates this file while target_os is netbsd; link the BSD libs
      # only in the matching toolchain context.
      libs = [
        "rt",
        "pthread",
      ]
    } else if (is_ios) {''')

# 12. perfetto BSD flag fallbacks
edit('third_party/perfetto/include/perfetto/base/build_config.h', '''#else
#error OS not supported (see build_config.h)
#endif''', '''#else
#error OS not supported (see build_config.h)
#endif

// EmberBSD cross profile (E12): non-BSD platform branches above do not
// define the BSD flags (added by the chromium-nb patchset), but sources
// such as base/event_fd.cc and base/android_utils.cc test them
// unconditionally when the host builds with a non-BSD toolchain.
// Default them to off there.
#ifndef PERFETTO_BUILDFLAG_DEFINE_PERFETTO_OS_BSD
#define PERFETTO_BUILDFLAG_DEFINE_PERFETTO_OS_BSD() 0
#endif
#ifndef PERFETTO_BUILDFLAG_DEFINE_PERFETTO_OS_OPENBSD
#define PERFETTO_BUILDFLAG_DEFINE_PERFETTO_OS_OPENBSD() 0
#endif
#ifndef PERFETTO_BUILDFLAG_DEFINE_PERFETTO_OS_NETBSD
#define PERFETTO_BUILDFLAG_DEFINE_PERFETTO_OS_NETBSD() 0
#endif
#ifndef PERFETTO_BUILDFLAG_DEFINE_PERFETTO_OS_FREEBSD
#define PERFETTO_BUILDFLAG_DEFINE_PERFETTO_OS_FREEBSD() 0
#endif''')

# 13. libc++ std::function policy helpers: no always_inline for GCC
edit('third_party/libc++/src/include/__functional/function.h', '''private:
  template <typename _Fun>
  _LIBCPP_HIDE_FROM_ABI static void* __large_clone(const void* __s) {
    const _Fun* __f = static_cast<const _Fun*>(__s);
    return new _Fun(*__f);
  }

  template <typename _Fun>
  _LIBCPP_HIDE_FROM_ABI static void __large_destroy(void* __s) {
    delete static_cast<_Fun*>(__s);
  }
};''', '''private:
// EmberBSD cross profile (E12): GCC rejects always_inline on these
// policy helpers once _Fun is a large Chromium template lambda
// (always_inline over budget is a hard error for GCC, and no --param
// combination allows it). Clang keeps the original attribute.
#if defined(__GNUC__) && !defined(__clang__)
#  define _LIBCPP_E12_POLICY_ATTR
#else
#  define _LIBCPP_E12_POLICY_ATTR _LIBCPP_HIDE_FROM_ABI
#endif
  template <typename _Fun>
  _LIBCPP_E12_POLICY_ATTR static void* __large_clone(const void* __s) {
    const _Fun* __f = static_cast<const _Fun*>(__s);
    return new _Fun(*__f);
  }

  template <typename _Fun>
  _LIBCPP_E12_POLICY_ATTR static void __large_destroy(void* __s) {
    delete static_cast<_Fun*>(__s);
  }
#undef _LIBCPP_E12_POLICY_ATTR
};''')

# 14. flat_tree deducible lookup params
s = open('base/containers/flat_tree.h').read()
s = s.replace('const KeyT<K>&', 'const K&')
marker = '''// --------------------------------------------------------------------------
  // Search operations.'''
comment = '''// EmberBSD cross profile (E12): GCC treats a KeyT<K> alias parameter as
  // a non-deduced context and always falls back to K = Key, rejecting the
  // heterogeneous lookups Clang accepts. Take the key as const K& instead:
  // the same instantiations resolve, and non-transparent comparators still
  // fail inside the body for mismatched key types.
'''
s = s.replace(marker, comment + marker, 1)
open('base/containers/flat_tree.h', 'w').write(s)

# 15. base fixes: ptrauth guard
edit('base/profiler/register_context_registers.h', '''#include <ptrauth.h>
#include <stdint.h>''', '''// EmberBSD cross profile (E12): ptrauth.h exists only in Apple SDKs;
// the unconditional include breaks NetBSD/arm64.
#if defined(__APPLE__)
#include <ptrauth.h>
#endif
#include <stdint.h>''')

# 16. base: epoll-shim include config
edit('base/BUILD.gn', '''config("asan_raw_ptr_service_v2_config") {''', '''# EmberBSD cross profile (E12): epoll-shim headers for NetBSD message loop
# live under the pkg prefix inside the cross sysroot when building from a
# macOS host; native NetBSD resolves them through the pkgsrc buildlink.
config("ember_epoll_shim_include") {
  cflags =
      [ "-isystem/private/tmp/ember-common-stack/sysroot/usr/pkg/include/libepoll-shim" ]
}

config("asan_raw_ptr_service_v2_config") {''')
edit('base/BUILD.gn', '''  # *BSD needs libkvm
  if (is_bsd) {
    libs += [
      "kvm",
      "epoll-shim",
    ]
  }''', '''  # *BSD needs libkvm
  if (is_bsd) {
    libs += [
      "kvm",
      "epoll-shim",
    ]

    # EmberBSD cross profile (E12): see the ember_epoll_shim_include config.
    if (is_netbsd && host_os == "mac") {
      configs += [ ":ember_epoll_shim_include" ]
    }
  }''')

# 17. base call-site key types (GCC transparent lookup)
for path, subs in {
 'base/values.cc': [
   ('storage_.insert_or_assign(key, std::move(wrapped_value));',
    'storage_.insert_or_assign(std::string(key), std::move(wrapped_value));'),
   ('storage_.insert_or_assign(storage_.end(), key, std::move(wrapped_value));',
    'storage_.insert_or_assign(storage_.end(), std::string(key), std::move(wrapped_value));'),
   ('storage_.insert_or_assign(key, std::make_unique<Value>(std::move(value)));',
    'storage_.insert_or_assign(std::string(key), std::make_unique<Value>(std::move(value)));'),
   ('return storage_.erase(key) > 0;', 'return storage_.erase(std::string(key)) > 0;'),
   ('auto it = storage_.find(key);', 'auto it = storage_.find(std::string(key));'),
   ('return storage_.contains(key);', 'return storage_.contains(std::string(key));'),
 ],
 'base/feature_list.cc': [
   ('overrides_.try_emplace(feature_name, overridden_state, field_trial);',
    'overrides_.try_emplace(std::string(feature_name), overridden_state, field_trial);'),
 ],
 'base/metrics/runtime_field_trial_overrides.cc': [
   ('auto previous_override = overrides_.find(previous_override_trial_name);',
    'auto previous_override = overrides_.find(std::string(previous_override_trial_name));'),
   ('auto it = overrides_.find(trial_name);',
    'auto it = overrides_.find(std::string(trial_name));'),
 ],
 'base/profiler/module_cache.cc': [
   ('const auto non_native_module_loc = non_native_modules_.find(address);',
    'const auto non_native_module_loc =\n        non_native_modules_.find<uintptr_t>(address);'),
 ],
}.items():
    if os.path.exists(path):
        s = open(path).read()
        for a, b in subs:
            s = s.replace(a, b)
        open(path, 'w').write(s)

# 18. build_ffmpeg.py cross support
edit('media/ffmpeg/scripts/build_ffmpeg.py', '''    if target_os.split('-', 1)[0] != host_os and (host_os != 'linux'
                                                  or host_arch != 'x64'):
        print('Cross compilation can only be done from a linux x64 host.')
        return 1''', '''    # EmberBSD cross profile (E12): allow generating configs from any host
    # when the cross toolchain prefix is provided by the build environment.
    # (A local `os` loop variable below shadows the os module in main().)
    import os as _ember_os
    ember_cross = _ember_os.environ.get('EMBER_FFMPEG_CROSS_PREFIX', '')

    if target_os.split('-', 1)[0] != host_os and (host_os != 'linux'
                                                  or host_arch != 'x64') \\
            and not ember_cross:
        print('Cross compilation can only be done from a linux x64 host.')
        return 1''')
edit('media/ffmpeg/scripts/build_ffmpeg.py', '''        elif target_arch == 'arm64':
            if target_os != 'android':
                if host_arch != 'arm64':''', '''        elif target_arch == 'arm64':
            if target_os != 'android':
                # EmberBSD cross profile (E12): honor the cross prefix from
                # the build environment instead of the linux-gnu default.
                ember_cross = os.environ.get('EMBER_FFMPEG_CROSS_PREFIX', '')
                if ember_cross:
                    configure_flags['Common'].extend([
                        '--enable-cross-compile',
                        '--cross-prefix=' + ember_cross,
                    ])
                elif host_arch != 'arm64':''')
edit('media/ffmpeg/scripts/build_ffmpeg.py', '''    if 'win' not in target_os and 'android' not in target_os:
        configure_flags['Common'].extend([
            '--enable-pic',
            '--cc=clang',
            '--cxx=clang++',
            '--ld=clang',
        ])''', '''    if 'win' not in target_os and 'android' not in target_os:
        # EmberBSD cross profile (E12): drive the configured cross toolchain
        # instead of host clang when the prefix is provided.
        ember_cc = os.environ.get('EMBER_FFMPEG_CROSS_PREFIX', '')
        if ember_cc:
            configure_flags['Common'].extend([
                '--enable-pic',
                '--cc=' + ember_cc + 'gcc',
                '--cxx=' + ember_cc + 'g++',
                '--ld=' + ember_cc + 'g++',
            ])
        else:
            configure_flags['Common'].extend([
                '--enable-pic',
                '--cc=clang',
                '--cxx=clang++',
                '--ld=clang',
            ])''')

print("adaptations applied")
PYEOF
git add -A
git -c user.name=ember-e12 -c user.email=e12@ember commit -qm "EmberBSD cross profile (E12): toolchains, SUBST equivalents, flag guards, flat_tree GCC deduction, libc++ GCC policies, base fixes, ffmpeg cross support"

echo "== tail patch (last two files) =="
patch --forward -p1 < /Users/smolev/Documents/prog/Claude/Projects/ember-wiki/.local/backups/e12-chromium-local-edits-20261017.patch || true
git add -A
git -c user.name=ember-e12 -c user.email=e12@ember commit -qm "EmberBSD cross (E12): immutable_string constexpr defaults, sequence_local_storage_slot template keyword (GCC)"

echo "== tool symlinks =="
mkdir -p third_party/rust-toolchain/bin
ln -sf "$HOME/.rustup/toolchains/nightly-2026-06-17-aarch64-apple-darwin/bin/rustc" third_party/rust-toolchain/bin/rustc
mkdir -p third_party/gperf/cipd/bin && ln -sf /usr/bin/gperf third_party/gperf/cipd/bin/gperf
mkdir -p third_party/node/netbsd/node-netbsd/bin
ln -sf /opt/homebrew/opt/node@24/bin/node third_party/node/netbsd/node-netbsd/bin/node
mkdir -p third_party/node/mac_arm64/node-darwin-arm64/bin
ln -sf /opt/homebrew/opt/node@24/bin/node third_party/node/mac_arm64/node-darwin-arm64/bin/node
mkdir -p sdk/xcode_links
ln -sfn "$SDK" sdk/xcode_links/MacOSX27.0.sdk

echo "== esbuild + rollup darwin =="
cp "$DIST/package/bin/esbuild" third_party/devtools-frontend/src/third_party/esbuild/esbuild
chmod +x third_party/devtools-frontend/src/third_party/esbuild/esbuild
mkdir -p third_party/devtools-frontend/src/node_modules/@rollup/rollup-darwin-arm64
tar -xzf "$DIST/rollup-darwin-arm64-4.60.4.tgz" -C third_party/devtools-frontend/src/node_modules/@rollup/rollup-darwin-arm64 --strip-components=1

echo "== ffmpeg configs =="
( cd media/ffmpeg && EMBER_FFMPEG_CROSS_PREFIX="$CROSSTOOLS/aarch64--netbsd-" \
    /opt/homebrew/bin/python3 scripts/build_ffmpeg.py netbsd arm64 --config-only --branding=Chrome >/dev/null )
B=third_party/ffmpeg/build.arm64.netbsd/Chrome
( cd "$B" && make libavutil/ffversion.h >/dev/null 2>&1 || true )
D=third_party/ffmpeg/chromium/config/Chrome/netbsd/arm64
mkdir -p "$D"
for p in config.h config_components.h libavcodec libavformat libavutil; do cp -pR "$B/$p" "$D/"; done

echo "== args.gn =="
mkdir -p out/e12
cat > out/e12/args.gn << 'ARGSEOF'
# EmberBSD cross arguments for the Electron/Chromium build (E12).
target_os = "netbsd"
target_cpu = "arm64"
custom_toolchain = "//build/toolchain/netbsd:gcc_arm64"
is_clang = false
use_lld = false
use_sysroot = false
is_debug = false
is_component_build = false
is_official_build = false
chrome_pgo_phase = 0
treat_warnings_as_errors = false
fatal_linker_warnings = false
use_partition_alloc = true
use_partition_alloc_as_malloc = false
use_custom_libcxx = true
use_qt5 = false
use_qt6 = false
use_kerberos = false
use_cups = false
use_sndio = false
use_vaapi = false
use_udev = true
disable_fieldtrial_testing_config = true
enable_backup_ref_ptr_support = false
emberbsd_target_sysroot = "/private/tmp/ember-common-stack/sysroot"
clang_base_path = "/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr"
extra_cxxflags = "-std=gnu++23"
use_system_xcode = true
clang_use_chrome_plugins = false
use_allocator_shim = false
ARGSEOF

echo "== gn bootstrap + gen =="
PATH="$CROSSTOOLS:/opt/homebrew/bin:$PATH" /opt/homebrew/bin/python3 tools/gn/bootstrap/bootstrap.py -o out/Release/gn >/dev/null 2>&1 || \
  PATH="$CROSSTOOLS:/opt/homebrew/bin:$PATH" /opt/homebrew/bin/python3 tools/gn/bootstrap/bootstrap.py -o out/Release/gn 2>&1 | tail -5
PATH="$CROSSTOOLS:/opt/homebrew/bin:$PATH" ./out/Release/gn gen out/e12 --script-executable=/opt/homebrew/bin/python3 2>&1 | tail -2
echo "== DONE: gn gen complete =="

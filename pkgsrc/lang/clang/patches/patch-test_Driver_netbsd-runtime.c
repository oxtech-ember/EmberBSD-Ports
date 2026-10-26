# Origin: EmberBSD contributors (AI-assisted), not submitted upstream.
# Driver regression for explicit target runtime selection, no target execution.

--- test/Driver/netbsd-runtime.c.orig
+++ test/Driver/netbsd-runtime.c
@@ -0,0 +1,43 @@
+// Explicit SDK runtime selection must work for both primary architectures.
+// The existing netbsd.c suite retains coverage of unconfigured base defaults.
+// RUN: %clang --no-default-config -### --target=aarch64-unknown-netbsd --sysroot=%S/Inputs/basic_netbsd_tree -resource-dir=%S/Inputs/resource_dir --rtlib=compiler-rt --unwindlib=none %s 2>&1 | FileCheck %s --check-prefix=CRT-A64 --implicit-check-not=-lgcc --implicit-check-not=-lunwind
+// RUN: %clang --no-default-config -### --target=x86_64-unknown-netbsd --sysroot=%S/Inputs/basic_netbsd_tree -resource-dir=%S/Inputs/resource_dir --rtlib=compiler-rt --unwindlib=none %s 2>&1 | FileCheck %s --check-prefix=CRT-X64 --implicit-check-not=-lgcc --implicit-check-not=-lunwind
+// RUN: %clang --no-default-config -### --target=aarch64-unknown-netbsd --sysroot=%S/Inputs/basic_netbsd_tree -resource-dir=%S/Inputs/resource_dir --rtlib=compiler-rt --unwindlib=libunwind -static %s 2>&1 | FileCheck %s --check-prefix=STATIC-UNWIND --implicit-check-not=-lgcc
+// RUN: %clang --no-default-config -### --target=x86_64-unknown-netbsd --sysroot=%S/Inputs/basic_netbsd_tree -resource-dir=%S/Inputs/resource_dir --rtlib=compiler-rt --unwindlib=libunwind -shared %s 2>&1 | FileCheck %s --check-prefix=SHARED-UNWIND --implicit-check-not=-lgcc
+// RUN: %clang --no-default-config -### --target=x86_64-unknown-netbsd --sysroot=%S/Inputs/basic_netbsd_tree -resource-dir=%S/Inputs/resource_dir --rtlib=compiler-rt --unwindlib=libunwind --driver-mode=g++ -stdlib=libc++ %s 2>&1 | FileCheck %s --check-prefix=CXX --implicit-check-not=-lgcc --implicit-check-not=-lstdc++
+// RUN: %clang --no-default-config -### --target=aarch64-unknown-netbsd --sysroot=%S/Inputs/basic_netbsd_tree --rtlib=libgcc --unwindlib=libgcc -static %s 2>&1 | FileCheck %s --check-prefix=STATIC-GCC --implicit-check-not=libclang_rt --implicit-check-not=-lunwind
+// RUN: %clang --no-default-config -### --target=x86_64-unknown-netbsd --sysroot=%S/Inputs/basic_netbsd_tree --rtlib=libgcc --unwindlib=libgcc -static %s 2>&1 | FileCheck %s --check-prefix=STATIC-GCC --implicit-check-not=libclang_rt --implicit-check-not=-lunwind
+// RUN: %clang --no-default-config -### --target=x86_64-unknown-netbsd --sysroot=%S/Inputs/basic_netbsd_tree --rtlib=libgcc --unwindlib=libgcc %s 2>&1 | FileCheck %s --check-prefix=SHARED-GCC --implicit-check-not=libclang_rt --implicit-check-not=-lunwind
+// RUN: %clang --no-default-config -### --target=aarch64-unknown-netbsd --sysroot=%S/Inputs/basic_netbsd_tree --rtlib=libgcc --unwindlib=none %s 2>&1 | FileCheck %s --check-prefix=GCC-NONE --implicit-check-not=libclang_rt --implicit-check-not=-lgcc_s --implicit-check-not=-lgcc_eh
+// RUN: %clang --no-default-config -### --target=aarch64-unknown-netbsd --sysroot=%S/Inputs/basic_netbsd_tree --rtlib=compiler-rt --unwindlib=libunwind -nostdlib %s 2>&1 | FileCheck %s --check-prefix=NO-RUNTIME --implicit-check-not=libclang_rt --implicit-check-not=-lunwind --implicit-check-not=-lgcc
+// RUN: %clang --no-default-config -### --target=x86_64-unknown-netbsd --sysroot=%S/Inputs/basic_netbsd_tree --rtlib=compiler-rt --unwindlib=libunwind -nodefaultlibs %s 2>&1 | FileCheck %s --check-prefix=NO-RUNTIME --implicit-check-not=libclang_rt --implicit-check-not=-lunwind --implicit-check-not=-lgcc
+// RUN: %clang --no-default-config -### --target=aarch64-unknown-netbsd --sysroot=%S/Inputs/basic_netbsd_tree --rtlib=compiler-rt --unwindlib=libunwind -r %s 2>&1 | FileCheck %s --check-prefix=NO-RUNTIME --implicit-check-not=libclang_rt --implicit-check-not=-lunwind --implicit-check-not=-lgcc
+// RUN: %clang --no-default-config -### --target=x86_64-unknown-netbsd --sysroot=%S/Inputs/basic_netbsd_tree --rtlib=compiler-rt --unwindlib=libunwind -nostartfiles %s 2>&1 | FileCheck %s --check-prefix=NO-START --implicit-check-not=crtbegin --implicit-check-not=crtend --implicit-check-not=-lgcc
+// RUN: not %clang --no-default-config -### --target=aarch64-unknown-netbsd --rtlib=invalid %s 2>&1 | FileCheck %s --check-prefix=BAD-RT
+// RUN: not %clang --no-default-config -### --target=x86_64-unknown-netbsd --rtlib=compiler-rt --unwindlib=invalid %s 2>&1 | FileCheck %s --check-prefix=BAD-UNWIND
+// RUN: not %clang --no-default-config -### --target=aarch64-unknown-netbsd --rtlib=libgcc --unwindlib=libunwind %s 2>&1 | FileCheck %s --check-prefix=INCOMPATIBLE
+
+// The common Ports recipe leaves CLANG_DEFAULT_RTLIB/UNWINDLIB unset.
+// NetBSD then defaults to libgcc; compiler-rt alone defaults to no unwinder.
+// RUN: %clang --no-default-config -### --target=aarch64-unknown-netbsd --sysroot=%S/Inputs/basic_netbsd_tree -resource-dir=%S/Inputs/resource_dir --rtlib=compiler-rt %s 2>&1 | FileCheck %s --check-prefix=CRT-A64 --implicit-check-not=-lgcc --implicit-check-not=-lunwind
+// RUN: %clang --no-default-config -### --target=x86_64-unknown-netbsd --sysroot=%S/Inputs/basic_netbsd_tree --rtlib=libgcc %s 2>&1 | FileCheck %s --check-prefix=SHARED-GCC --implicit-check-not=libclang_rt --implicit-check-not=-lunwind
+// RUN: %clang --no-default-config -### --target=x86_64-unknown-netbsd --sysroot=%S/Inputs/basic_netbsd_tree --unwindlib=libgcc %s 2>&1 | FileCheck %s --check-prefix=SHARED-GCC --implicit-check-not=libclang_rt --implicit-check-not=-lunwind
+// RUN: %clang --no-default-config -### --target=aarch64-unknown-netbsd --sysroot=%S/Inputs/basic_netbsd_tree --unwindlib=none %s 2>&1 | FileCheck %s --check-prefix=GCC-NONE --implicit-check-not=libclang_rt --implicit-check-not=-lgcc_s --implicit-check-not=-lgcc_eh
+// RUN: not %clang --no-default-config -### --target=aarch64-unknown-netbsd --unwindlib=libunwind %s 2>&1 | FileCheck %s --check-prefix=INCOMPATIBLE
+
+// CRT-A64: "{{.*}}libclang_rt.builtins-aarch64.a" "-lc" "{{.*}}libclang_rt.builtins-aarch64.a"
+// CRT-X64: "{{.*}}libclang_rt.builtins-x86_64.a" "-lc" "{{.*}}libclang_rt.builtins-x86_64.a"
+// STATIC-UNWIND: "-Bstatic"
+// STATIC-UNWIND-SAME: "{{.*}}libclang_rt.builtins-aarch64.a" "-l:libunwind.a" "-lc" "{{.*}}libclang_rt.builtins-aarch64.a" "-l:libunwind.a"
+// SHARED-UNWIND: "-shared"
+// SHARED-UNWIND-SAME: "{{.*}}libclang_rt.builtins-x86_64.a" "--as-needed" "-lunwind" "--no-as-needed" "-lc" "{{.*}}libclang_rt.builtins-x86_64.a" "--as-needed" "-lunwind" "--no-as-needed"
+// CXX: "-lc++" "-lm" "{{.*}}libclang_rt.builtins-x86_64.a" "--as-needed" "-lunwind" "--no-as-needed" "-lc" "{{.*}}libclang_rt.builtins-x86_64.a" "--as-needed" "-lunwind" "--no-as-needed"
+// STATIC-GCC: "-Bstatic"
+// STATIC-GCC-SAME: "-lgcc" "-lgcc_eh" "-lc" "-lgcc" "-lgcc_eh"
+// SHARED-GCC: "-lgcc" "--as-needed" "-lgcc_s" "--no-as-needed" "-lc" "-lgcc" "--as-needed" "-lgcc_s" "--no-as-needed"
+// GCC-NONE: "-lgcc" "-lc" "-lgcc"
+// NO-RUNTIME: "-o" "a.out"
+// NO-START: "{{.*}}libclang_rt.builtins-x86_64.a" "--as-needed" "-lunwind" "--no-as-needed" "-lc" "{{.*}}libclang_rt.builtins-x86_64.a"
+// BAD-RT: error: invalid runtime library name in argument '{{.*}}rtlib=invalid'
+// BAD-UNWIND: error: invalid unwind library name in argument '{{.*}}unwindlib=invalid'
+// INCOMPATIBLE: error: --rtlib=libgcc requires --unwindlib=libgcc

# Origin: EmberBSD contributors (AI-assisted), not submitted upstream.

--- /dev/null
+++ test/Driver/netbsd-lto.c
@@ -0,0 +1,14 @@
+// Driver-only proposal; real selected LLD links and runtime tested separately.
+// RUN: mkdir -p %t && ln -sf %clang %t/ld.lld && ln -sf %clang %t/ld.bfd
+// RUN: %clang --no-default-config -### --target=aarch64-unknown-netbsd --ld-path=%t/ld.lld -flto -O2 %s 2>&1 | FileCheck %s --check-prefix=FULL --implicit-check-not='unable to pass LLVM bit-code' --implicit-check-not=LLVMgold
+// RUN: %clang --no-default-config -### --target=aarch64-unknown-netbsd --ld-path=%t/ld.lld -flto=thin -O2 %s 2>&1 | FileCheck %s --check-prefix=THIN --implicit-check-not='unable to pass LLVM bit-code' --implicit-check-not=LLVMgold
+// RUN: %clang --no-default-config -### --target=aarch64-unknown-netbsd --ld-path=%t/ld.lld -fuse-ld=lld -flto -O2 %s 2>&1 | FileCheck %s --check-prefix=FULL --implicit-check-not='unable to pass LLVM bit-code' --implicit-check-not=LLVMgold
+// RUN: %clang --no-default-config -### --target=aarch64-unknown-netbsd --ld-path=%t/ld.lld -fuse-ld=lld -flto=thin -O2 %s 2>&1 | FileCheck %s --check-prefix=THIN --implicit-check-not='unable to pass LLVM bit-code' --implicit-check-not=LLVMgold
+// RUN: not %clang --no-default-config -### --target=aarch64-unknown-netbsd --ld-path=%t/ld.bfd -fuse-ld=bfd -flto %s 2>&1 | FileCheck %s --check-prefix=UNSUPPORTED
+// RUN: %clang --no-default-config -### --target=aarch64-unknown-netbsd --ld-path=%t/ld.bfd -fuse-ld=bfd %s 2>&1 | FileCheck %s --check-prefix=NO-LTO --implicit-check-not='unable to pass LLVM bit-code'
+// FULL: "-plugin-opt=O2"
+// FULL-NOT: "-plugin-opt=thinlto"
+// THIN: "-plugin-opt=thinlto"
+// UNSUPPORTED: unable to pass LLVM bit-code files to linker
+// NO-LTO: "-lc"
+int main(void) { return 0; }

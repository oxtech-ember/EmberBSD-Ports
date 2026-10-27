$NetBSD$

Select source-built EmberBSD/NetBSD N-API bindings through the upstream loader.
Keep its missing-module and dlopen diagnostics.

--- npm/package/dist/native.js.orig
+++ npm/package/dist/native.js
@@ -74,6 +74,10 @@
 		riscv64: { base: 'linux-riscv64-gnu', musl: 'linux-riscv64-musl' },
 		s390x: { base: 'linux-s390x-gnu', musl: null },
 		x64: { base: 'linux-x64-gnu', musl: 'linux-x64-musl' }
+	},
+	netbsd: {
+		arm64: { base: 'netbsd-arm64' },
+		x64: { base: 'netbsd-x64' }
 	},
 	openbsd: {
 		x64: { base: 'openbsd-x64' }

$NetBSD: patch-src_cmd_dist_build.go,v 1.1 2026/08/22 18:49:07 bsiegert Exp $

Keep debug symbols in the installed Go tools. Trim source paths on NetBSD
and Darwin. Both systems locate the executable without procfs. Keep the
embedded GOROOT on other systems for installations without procfs.

--- src/cmd/dist/build.go.orig
+++ src/cmd/dist/build.go
@@ -1391,13 +1391,8 @@
 		// as the original build system.
 		env = append(env, "CGO_ENABLED=0")
 	}
-	if isRelease || os.Getenv("GO_BUILDER_NAME") != "" {
-		// Add -trimpath for reproducible builds of releases.
-		// Include builders so that -trimpath is well-tested ahead of releases.
-		// Do not include local development, so that people working in the
-		// main branch for day-to-day work on the Go toolchain itself can
-		// still have full paths for stack traces for compiler crashes and the like.
-		env = append(env, "GOFLAGS=-trimpath -ldflags=-w -gcflags=cmd/...=-dwarf=false")
+	if (isRelease || os.Getenv("GO_BUILDER_NAME") != "") && (goos == "netbsd" || goos == "darwin") {
+		env = append(env, "GOFLAGS=-trimpath")
 	}
 	return env
 }

$NetBSD$

EmberBSD: a cross-built toolchain does not record the build host compiler
that cmd/dist keeps for host programs as an installed default.

--- src/cmd/dist/buildgo.go.orig
+++ src/cmd/dist/buildgo.go
@@ -7,6 +7,7 @@
 import (
 	"fmt"
 	"io"
+	"os"
 	"path/filepath"
 	"sort"
 	"strings"
@@ -50,8 +51,8 @@
 		fmt.Fprintf(&buf, "package cfg\n")
 		fmt.Fprintln(&buf)
 		fmt.Fprintf(&buf, "const DefaultPkgConfig = `%s`\n", defaultpkgconfig)
-		buf.WriteString(defaultCCFunc("DefaultCC", defaultcc))
-		buf.WriteString(defaultCCFunc("DefaultCXX", defaultcxx))
+		buf.WriteString(defaultCCFunc("DefaultCC", installedCompilers("CC", defaultcc)))
+		buf.WriteString(defaultCCFunc("DefaultCXX", installedCompilers("CXX", defaultcxx)))
 		writefile(buf.String(), file, writeSkipSame)
 		return
 	}
@@ -61,11 +62,34 @@
 	fmt.Fprintf(&buf, "package main\n")
 	fmt.Fprintln(&buf)
 	fmt.Fprintf(&buf, "const defaultPkgConfig = `%s`\n", defaultpkgconfig)
-	buf.WriteString(defaultCCFunc("defaultCC", defaultcc))
-	buf.WriteString(defaultCCFunc("defaultCXX", defaultcxx))
+	buf.WriteString(defaultCCFunc("defaultCC", installedCompilers("CC", defaultcc)))
+	buf.WriteString(defaultCCFunc("defaultCXX", installedCompilers("CXX", defaultcxx)))
 	writefile(buf.String(), file, writeSkipSame)
 }
 
+// installedCompilers returns the compiler map that the built toolchain
+// records as its defaults. When cmd/dist builds a toolchain for another
+// platform with CC_FOR_TARGET or CXX_FOR_TARGET, compilerEnv keeps the build
+// host's CC or CXX under gohostos/gohostarch so that host programs can be
+// built. The installed toolchain runs on goos/goarch, where that build-host
+// command does not exist, so it is left out unless it was given explicitly
+// as CC_FOR_<gohostos>_<gohostarch> or CXX_FOR_<gohostos>_<gohostarch>.
+// (EmberBSD)
+func installedCompilers(envName string, m map[string]string) map[string]string {
+	host := gohostos + "/" + gohostarch
+	if host == goos+"/"+goarch || m[host] == "" ||
+		os.Getenv(envName+"_FOR_"+gohostos+"_"+gohostarch) != "" {
+		return m
+	}
+	installed := make(map[string]string, len(m))
+	for k, v := range m {
+		if k != host {
+			installed[k] = v
+		}
+	}
+	return installed
+}
+
 func defaultCCFunc(name string, defaultcc map[string]string) string {
 	var buf strings.Builder
 

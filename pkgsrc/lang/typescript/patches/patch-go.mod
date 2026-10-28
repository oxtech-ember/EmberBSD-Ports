# $NetBSD$

# Use the common current Go dependency.
# Origin: EmberBSD (AI-assisted).

--- go.mod.orig
+++ go.mod
@@ -1,6 +1,6 @@
 module github.com/microsoft/typescript-go
 
-go 1.26
+go 1.26.0
 
 require (
 	github.com/Microsoft/go-winio v0.6.2
@@ -10,7 +10,7 @@
 	github.com/peter-evans/patience v0.3.0
 	github.com/zeebo/xxh3 v1.1.0
 	golang.org/x/sync v0.21.0
-	golang.org/x/sys v0.46.0
+	golang.org/x/sys v0.49.0
 	golang.org/x/term v0.44.0
 	golang.org/x/text v0.38.0
 	gotest.tools/v3 v3.5.2

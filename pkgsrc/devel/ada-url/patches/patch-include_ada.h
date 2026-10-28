# $NetBSD$

Use shared ada-idna and shared test dependencies.

--- include/ada.h.orig
+++ include/ada.h
@@ -28,7 +28,7 @@
 #ifndef ADA_H
 #define ADA_H
 
-#include "ada/ada_idna.h"
+#include <idna.h>
 #include "ada/character_sets.h"
 #include "ada/character_sets-inl.h"
 #include "ada/checkers-inl.h"

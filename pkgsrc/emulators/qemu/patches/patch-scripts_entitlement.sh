$NetBSD$

Use the selected native Darwin tools and preserve the Mach-O data fork.

--- scripts/entitlement.sh.orig
+++ scripts/entitlement.sh
@@ -22,12 +22,13 @@
 fi
 
 if test -n "$ENTITLEMENT"; then
-  codesign --entitlements "$ENTITLEMENT" --force -s - "$SRC"
+  CODESIGN_ALLOCATE="@TOOLBASE@/bin/codesign_allocate" \
+    "@TOOLBASE@/bin/codesign" --entitlements "$ENTITLEMENT" --force -s - "$SRC"
 fi
 
 # Add the QEMU icon to the binary on Mac OS
-Rez -append "$ICON" -o "$SRC"
-SetFile -a C "$SRC"
+"@TOOLBASE@/bin/Rez" --input-format=text --resource-fork-only --append "$ICON" -o "$SRC"
+"@TOOLBASE@/bin/setfflags" -c true "$SRC"
 
 mv -f "$SRC" "$DST"
 trap '' exit

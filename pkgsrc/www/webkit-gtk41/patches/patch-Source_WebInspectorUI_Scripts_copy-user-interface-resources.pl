$NetBSD$

Use the existing portable recursive copy path on Darwin hosts.
The selected build environment does not provide Apple's ditto utility.

--- Source/WebInspectorUI/Scripts/copy-user-interface-resources.pl.orig	2026-04-19 05:55:05.008914400 +0000
+++ Source/WebInspectorUI/Scripts/copy-user-interface-resources.pl
@@ -56,8 +56,6 @@
 
     if ($useDirCopy) {
         File::Copy::Recursive::dircopy($source, $destination) or die "Unable to copy directory $source to $destination: $!";
-    } elsif ($^O eq 'darwin') {
-        system('ditto', $source, $destination);
     } elsif ($^O ne 'MSWin32') {
         # Ditto copies the *contents* of the source directory, not the directory itself.
         opendir(my $dh, $source) or die "Can't open $source: $!";

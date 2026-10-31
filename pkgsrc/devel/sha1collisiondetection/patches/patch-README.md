$NetBSD$

Bring upstream documentation to the same post-release source revision.
Origin: https://github.com/cr-marcstevens/sha1collisiondetection/compare/stable-v1.0.3...a06f1adbe5522f3c939cd6a3f13d5ec7f4c1a988

--- README.md.orig
+++ README.md
@@ -44,13 +44,15 @@
 ## Command-line usage
 
 There are two programs `bin/sha1dcsum` and `bin/sha1dcsum_partialcoll`.
-The first program `bin/sha1dcsum` will detect and warn for files that were generated with a cryptanalytic SHA-1 collision attack like the one documented at https://shattered.io/.
+The first program `bin/sha1dcsum` will detect and warn for files that were generated with a cryptanalytic SHA-1 collision attack,
+like the one documented at https://shattered.io/ as well as the later derived attack https://sha-mbles.github.io/.
 The second program `bin/sha1dcsum_partialcoll` will detect and warn for files that were generated with a cryptanalytic collision attack against reduced-round SHA-1 (of which there are a few examples so far).
 
 Examples:
 ```
 bin/sha1dcsum test/sha1_reducedsha_coll.bin test/shattered-1.pdf
 bin/sha1dcsum_partialcoll test/sha1reducedsha_coll.bin test/shattered-1.pdf
+pipe_data | bin/sha1dcsum -
 ```
 
 ## Library usage
@@ -77,3 +79,68 @@
     printf("no collision detected");
 ```
 
+## Inclusion in other programs
+
+In order to make it easier to include these sources in other project
+there are several preprocessor macros that the code uses. Rather than
+copy/pasting and customizing or specializing the code, first see if
+setting any of these defines appropriately will allow you to avoid
+modifying the code yourself.
+
+- SHA1DC_NO_STANDARD_INCLUDES
+
+ Skips including standard headers. Use this if your project for
+ whatever reason wishes to do its own header includes.
+
+- SHA1DC_CUSTOM_INCLUDE_SHA1_C
+
+  Includes a custom header at the top of sha1.c. Usually this would be
+  set in conjunction with SHA1DC_NO_STANDARD_INCLUDES to point to a
+  header file which includes various standard headers.
+
+- SHA1DC_INIT_SAFE_HASH_DEFAULT
+
+  Sets the default for safe_hash in SHA1DCInit(). Valid values are 0
+  and 1. If unset 1 is the default.
+
+- SHA1DC_CUSTOM_TRAILING_INCLUDE_SHA1_C
+
+  Includes a custom trailer in sha1.c. Useful for any extra utility
+  functions that make use of the functions already defined in sha1.c.
+
+- SHA1DC_CUSTOM_TRAILING_INCLUDE_SHA1_H
+
+  Includes a custom trailer in sha1.h. Useful for defining the
+  prototypes of the functions or code included by
+  SHA1DC_CUSTOM_TRAILING_INCLUDE_SHA1_C.
+
+- SHA1DC_CUSTOM_INCLUDE_UBC_CHECK_C
+
+  Includes a custom header at the top of ubc_check.c.
+
+- SHA1DC_CUSTOM_TRAILING_INCLUDE_UBC_CHECK_C
+
+  Includes a custom trailer in ubc_check.c.
+
+- SHA1DC_CUSTOM_TRAILING_INCLUDE_UBC_CHECK_H
+
+  Includes a custom trailer in ubc_check.H.
+
+This code will try to auto-detect certain things based on
+CPU/platform. Unless you're running on some really obscure CPU or
+porting to a new platform you should not need to tweak this. If you do
+please open an issue at
+https://github.com/cr-marcstevens/sha1collisiondetection
+
+- SHA1DC_FORCE_LITTLEENDIAN / SHA1DC_FORCE_BIGENDIAN
+
+  Override the check for processor endianenss and force either
+  Little-Endian or Big-Endian.
+
+- SHA1DC_FORCE_UNALIGNED_ACCESS
+
+  Permit unaligned access. This will fail on e.g. SPARC processors, so
+  it's only permitted on a whitelist of processors. If your CPU isn't
+  detected as allowing this, and allows unaligned access, setting this
+  may improve performance (or make it worse, if the kernel has to
+  catch and emulate such access on its own).

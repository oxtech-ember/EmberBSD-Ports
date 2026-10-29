$NetBSD$

Include the standard declaration for make_unique.

--- tools/debugserver/source/MacOSX/MachVMMemory.cpp.orig
+++ tools/debugserver/source/MacOSX/MachVMMemory.cpp
@@ -14,6 +14,7 @@
 #include "DNBLog.h"
 #include "MachVMRegion.h"
 #include <cassert>
+#include <memory>
 #include <dlfcn.h>
 #include <mach/mach_vm.h>
 #include <mach/shared_region.h>

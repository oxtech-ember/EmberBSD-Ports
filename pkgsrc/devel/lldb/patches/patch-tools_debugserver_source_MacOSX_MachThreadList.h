$NetBSD$

Include the standard declaration for shared_ptr used by MachThreadList.

--- tools/debugserver/source/MacOSX/MachThreadList.h.orig
+++ tools/debugserver/source/MacOSX/MachThreadList.h
@@ -16,6 +16,8 @@
 #include "MachThread.h"
 #include "ThreadInfo.h"
 
+#include <memory>
+
 class DNBThreadResumeActions;
 
 class MachThreadList {

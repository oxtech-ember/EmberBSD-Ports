$NetBSD$

Handle processing units without Core ancestors, as exposed by some OS and
virtual-machine hwloc backends. Preserve existing SMT core grouping.

--- include/tmc/detail/thread_layout.ipp.orig
+++ include/tmc/detail/thread_layout.ipp
@@ -1068,7 +1068,13 @@
     TopologyCore* core = nullptr;
     while (true) {
       if (childIdx.back() == 0) {
-        if (curr->type == HWLOC_OBJ_CORE) {
+        // Some operating systems and virtual machines expose PUs without
+        // Core objects. Treat each such PU as a scheduling core, while
+        // preserving the grouping of PUs that do have a Core ancestor.
+        if (curr->type == HWLOC_OBJ_CORE ||
+            (curr->type == HWLOC_OBJ_PU &&
+             hwloc_get_ancestor_obj_by_type(topo, HWLOC_OBJ_CORE, curr) ==
+               nullptr)) {
           size_t kind = 0;
           for (size_t i = 0; i < kindCpuSets.size(); ++i) {
             if (hwloc_bitmap_intersects(kindCpuSets[i], curr->cpuset)) {
@@ -1131,10 +1137,8 @@
           core->cache = cache;
           core->numa = numa;
           core->cpu_kind = kind;
-        } else if (curr->type == HWLOC_OBJ_PU) {
-          // Assume we can use the "core" as the smallest unit, and that PUs
-          // will always be descendants of cores. This doesn't work on IBM
-          // PPC64.
+        }
+        if (curr->type == HWLOC_OBJ_PU) {
           core->pus.push_back(curr);
         }
       }

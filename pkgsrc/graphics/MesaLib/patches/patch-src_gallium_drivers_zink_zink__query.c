$NetBSD$

Free the allocated query when the query type has no Vulkan mapping.
Origin: EmberBSD contributors (AI-assisted). SPDX-License-Identifier: MIT.

--- src/gallium/drivers/zink/zink_query.c.orig
+++ src/gallium/drivers/zink/zink_query.c
@@ -528,8 +528,10 @@
    if (query->type == PIPE_QUERY_GPU_FINISHED || query->type == PIPE_QUERY_TIMESTAMP_DISJOINT)
       return (struct pipe_query *)query;
    query->vkqtype = convert_query_type(screen, query_type, &query->precise);
-   if (query->vkqtype == -1)
+   if (query->vkqtype == -1) {
+      free(query);
       return NULL;
+   }
 
    query->starts = UTIL_DYNARRAY_INIT;
 

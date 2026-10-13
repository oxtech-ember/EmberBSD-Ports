$NetBSD$

Origin: EmberBSD (AI-assisted).
Match the signed int type of __LINE__ in the existing BUG_WARN message.
Keep message text, control flow, and protocol handling unchanged.

--- include/misc.h.orig
+++ include/misc.h
@@ -416,7 +416,7 @@
 #define __BUG_WARN_MSG(cond, with_msg, ...)                                \
           do { if (cond) {                                                \
               ErrorFSigSafe("BUG: triggered 'if (" #cond ")'\n");          \
-              ErrorFSigSafe("BUG: %s:%u in %s()\n",                        \
+              ErrorFSigSafe("BUG: %s:%d in %s()\n",                        \
                            __FILE__, __LINE__, __func__);                 \
               if (with_msg) ErrorFSigSafe(__VA_ARGS__);                    \
               xorg_backtrace();                                           \

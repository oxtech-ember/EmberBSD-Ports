$NetBSD$

Locate the smbtorture helper in the configured build or installation tree.

--- lib/util/tests/tfork.c.orig
+++ lib/util/tests/tfork.c
@@ -18,6 +18,7 @@
  */
 
 #include "replace.h"
+#include "dynconfig/dynconfig.h"
 #include <talloc.h>
 #include <tevent.h>
 #include "system/filesys.h"
@@ -535,7 +536,7 @@
 	torture_assert_goto(tctx, ev != NULL, ok, done,
 			    "tevent_context_init failed\n");
 
-	cmd[0] = talloc_asprintf(tctx, "%s/testprogs/blackbox/tfork.sh", SRCDIR);
+	cmd[0] = talloc_asprintf(tctx, "%s/tfork.sh", get_dyn_SAMBA_LIBEXECDIR());
 	torture_assert_goto(tctx, cmd[0] != NULL, ok, done,
 			    "talloc_asprintf failed\n");
 

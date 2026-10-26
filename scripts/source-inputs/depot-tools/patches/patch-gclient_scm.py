Recover interrupted SYNC dependencies before trusting the parent gitlink.
Origin: Chromium depot_tools b86fc981b72ab966f8260f73b4eca600b3b12677.
The existing upstream quarantine/reclone path preserves the broken checkout;
this does not request force, reset, or hook execution.

--- a/gclient_scm.py
+++ b/gclient_scm.py
@@ -1127,12 +1127,16 @@
         # information already.
         if rev_type == "hash":
             if self.current_revision == revision:
+                # A matching parent gitlink does not prove that checkout
+                # completed. Preserve and recover an interrupted child using
+                # the same invalid-HEAD path as ordinary DEPS dependencies.
+                self.current_revision = self._EnsureValidHeadObjectOrCheckout(
+                    revision, options, url
+                )
+            if self.current_revision == revision:
                 if verbose:
                     self.Print("Using submodule information to skip check")
                 if options.reset or options.force:
-                    self._EnsureValidHeadObjectOrCheckout(
-                        revision, options, url
-                    )
                     self._Scrub("HEAD", options)
 
                 return revision

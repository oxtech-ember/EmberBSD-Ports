Preserve errno guards for the compiler; config.h does not define errno.

--- cf/roken-h-process.pl.orig
+++ cf/roken-h-process.pl
@@ -76,7 +76,14 @@
 @nesting = (1);
 
 while (<IN>) {
-    if (m/\s*#ifdef\s+(.*)/) {
+    # errno names come from system headers, not configure's config.h.
+    # Keep these guards for the compiler, while evaluating the surrounding
+    # configure-dependent conditions as before.
+    if (m/^\s*#ifndef\s+(EAFNOSUPPORT|EINPROGRESS|ELOOP|ENOTSOCK|ENOTSUP|EOVERFLOW|ETIMEDOUT|EWOULDBLOCK)\s*$/) {
+        print OUT if !grep { $_ <= 0 } @nesting;
+        push @nesting, 2;
+        next;
+    } elsif (m/\s*#ifdef\s+(.*)/) {
 	my $var = $1;
 	if (defined $defines{$var}) {
 	    push @nesting, 1;
@@ -112,8 +119,9 @@
 	push @nesting, $var;
 	next;
     } elsif (m/\s*#endif/) {
-	pop @nesting;
-	next;
+        my $scope = pop @nesting;
+        print OUT if $scope == 2 && !grep { $_ <= 0 } @nesting;
+        next;
     }
     print "line: $_\n"  if ($debug);
     print "nesting dep $#{nesting}\n"  if ($debug);

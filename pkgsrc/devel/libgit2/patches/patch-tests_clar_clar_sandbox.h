$NetBSD$

Use unsigned arithmetic for the test harness random seed.

--- tests/clar/clar/sandbox.h.orig
+++ tests/clar/clar/sandbox.h
@@ -191,7 +191,7 @@
 #if !defined(CLAR_SANDBOX_TEST_NAMES) && defined(_WIN32)
 	srand(clock() ^ (unsigned int)time(NULL) ^ GetCurrentProcessId() ^ GetCurrentThreadId());
 #elif !defined(CLAR_SANDBOX_TEST_NAMES)
-	srand(clock() ^ time(NULL) ^ (getpid() << 16));
+	srand(clock() ^ time(NULL) ^ ((unsigned int)getpid() << 16));
 #endif
 }
 

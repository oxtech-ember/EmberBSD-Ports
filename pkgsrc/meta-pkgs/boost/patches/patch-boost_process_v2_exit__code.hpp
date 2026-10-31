$NetBSD$

NetBSD's <sys/wait.h> reads the status through _W_INT(w), which is
*(int *)(void *)&(w). A cast from void * is not a constant expression
before C++26, so Clang rejects the static_asserts on the wait macros.
Check the same definitions on the value itself on NetBSD.

--- boost/process/v2/exit_code.hpp.orig
+++ boost/process/v2/exit_code.hpp
@@ -73,10 +73,28 @@
 namespace detail
 {
 constexpr native_exit_code_type still_active = 0x17f;
+#if defined(__NetBSD__)
+// NetBSD's <sys/wait.h> reads the status through _W_INT(w), which is
+// *(int *)(void *)&(w) for union wait. A cast from void * is not a
+// constant expression before C++26, so apply the same definitions
+// (_WSTATUS is the low 0177 bits) to the value itself.
+constexpr bool still_active_continued =
+    static_cast<unsigned int>(still_active) == _WCONTINUED;
+constexpr bool still_active_exited = (still_active & 0177) == 0;
+constexpr bool still_active_stopped =
+    (still_active & 0177) == _WSTOPPED && !still_active_continued;
+constexpr bool still_active_signaled =
+    !still_active_stopped && !still_active_continued && !still_active_exited;
+static_assert(still_active_stopped, "Expected still_active to indicate WIFSTOPPED");
+static_assert(!still_active_exited, "Expected still_active to not indicate WIFEXITED");
+static_assert(!still_active_signaled, "Expected still_active to not indicate WIFSIGNALED");
+static_assert(!still_active_continued, "Expected still_active to not indicate WIFCONTINUED");
+#else
 static_assert(WIFSTOPPED(still_active), "Expected still_active to indicate WIFSTOPPED");
 static_assert(!WIFEXITED(still_active), "Expected still_active to not indicate WIFEXITED");
 static_assert(!WIFSIGNALED(still_active), "Expected still_active to not indicate WIFSIGNALED");
 static_assert(!WIFCONTINUED(still_active), "Expected still_active to not indicate WIFCONTINUED");
+#endif
 }
 
 inline bool process_is_running(int code)

$NetBSD$

NetBSD port of the thread helpers: cpuset_t affinity through
cpuset_create(3), the printf-style pthread_setname_np(3), and no
SCHED_RESET_ON_FORK policy flag.

--- src/pipewire/thread.c.orig
+++ src/pipewire/thread.c
@@ -6,6 +6,10 @@
 #include <unistd.h>
 #include <sys/types.h>
 #include <pthread.h>
+#ifdef __NetBSD__
+#include <sched.h>
+#include <stdint.h>
+#endif
 #ifdef __FreeBSD__
 #include <pthread_np.h>
 #endif
@@ -29,6 +33,7 @@
 	}								\
 } while(false);
 
+#ifndef __NetBSD__
 static int parse_affinity(const char *affinity, cpu_set_t *set)
 {
 	struct spa_json it[1];
@@ -44,6 +49,7 @@
         }
 	return 0;
 }
+#endif
 
 SPA_EXPORT
 void *pw_thread_fill_attr(const struct spa_dict *props, void *_attr)
@@ -78,6 +84,38 @@
 int pthread_setname_np(pthread_t thread, const char *name) { return 0; }
 #endif
 
+#ifdef __NetBSD__
+/*
+ * NetBSD has an opaque cpuset_t sized at run time and no CPU_SET macros.
+ * CPUs the kernel does not know are ignored, as CPUs past CPU_SETSIZE are
+ * on Linux.
+ */
+static int thread_setaffinity(pthread_t thread, const char *affinity)
+{
+	struct spa_json it[1];
+	cpuset_t *set;
+	int v, res;
+
+	if ((set = cpuset_create()) == NULL)
+		return -errno;
+	cpuset_zero(set);
+	if (spa_json_begin_array_relax(&it[0], affinity, strlen(affinity)) > 0) {
+		while (spa_json_get_int(&it[0], &v) > 0) {
+			if (v >= 0)
+				(void)cpuset_set((cpuid_t)v, set);
+		}
+	}
+	res = -pthread_setaffinity_np(thread, cpuset_size(set), set);
+	cpuset_destroy(set);
+	return res;
+}
+
+/* NetBSD takes a printf format and one argument for the name. */
+static int thread_setname(pthread_t thread, const char *name)
+{
+	return pthread_setname_np(thread, "%s", (void *)(uintptr_t)name);
+}
+#else
 static int thread_setaffinity(pthread_t thread, const char *affinity)
 {
 	cpu_set_t set;
@@ -85,6 +123,12 @@
 	return -pthread_setaffinity_np(thread, sizeof(set), &set);
 }
 
+static int thread_setname(pthread_t thread, const char *name)
+{
+	return pthread_setname_np(thread, name);
+}
+#endif
+
 static struct spa_thread *impl_create(void *object,
 			const struct spa_dict *props,
 			void *(*start)(void*), void *arg)
@@ -115,7 +159,7 @@
 	}
 	if (props) {
 		if ((str = spa_dict_lookup(props, SPA_KEY_THREAD_NAME)) != NULL &&
-		    (err = pthread_setname_np(pt, str)) != 0)
+		    (err = thread_setname(pt, str)) != 0)
 			pw_log_warn("pthread_setname error: %s", strerror(err));
 		if ((str = spa_dict_lookup(props, SPA_KEY_THREAD_AFFINITY)) != NULL &&
 		    (err = thread_setaffinity(pt, str)) != 0)
@@ -124,11 +168,16 @@
 			reset_on_fork = spa_atob(str);
 	}
 
+#ifdef SCHED_RESET_ON_FORK
 	pthread_getschedparam(pt, &old_policy, &sp);
 	new_policy = old_policy;
 	SPA_FLAG_UPDATE(new_policy, SCHED_RESET_ON_FORK, reset_on_fork);
 	if (old_policy != new_policy)
 		pthread_setschedparam(pt, new_policy, &sp);
+#else
+	/* No reset-on-fork policy flag (NetBSD): nothing to change. */
+	(void)old_policy; (void)new_policy; (void)sp; (void)reset_on_fork;
+#endif
 
 	return (struct spa_thread*)pt;
 }

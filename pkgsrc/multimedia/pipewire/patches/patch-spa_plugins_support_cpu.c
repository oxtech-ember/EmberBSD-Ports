$NetBSD$

NetBSD: count the CPUs in the affinity set (cpuset_t), else the online CPUs.

--- spa/plugins/support/cpu.c.orig
+++ spa/plugins/support/cpu.c
@@ -92,7 +92,30 @@
 	return 0;
 }
 
-#ifndef __FreeBSD__
+#if defined(__NetBSD__)
+static uint32_t get_count(struct impl *this)
+{
+	cpuset_t *set;
+	cpuid_t i;
+	uint32_t count = 0;
+	long n;
+
+	if ((set = cpuset_create()) != NULL) {
+		if (sched_getaffinity_np(getpid(), cpuset_size(set), set) == 0) {
+			/* cpuset_isset() returns -1 past the end of the set. */
+			for (i = 0; cpuset_isset(i, set) >= 0; i++)
+				if (cpuset_isset(i, set) > 0)
+					count++;
+		}
+		cpuset_destroy(set);
+	}
+	if (count > 0)
+		return count;
+	/* An empty affinity mask means the process may run on any online CPU. */
+	n = sysconf(_SC_NPROCESSORS_ONLN);
+	return n > 0 ? (uint32_t)n : 1;
+}
+#elif !defined(__FreeBSD__)
 static uint32_t get_count(struct impl *this)
 {
 	cpu_set_t cpuset;

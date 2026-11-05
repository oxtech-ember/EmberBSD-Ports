$NetBSD$

Preserve basic NetBSD support from https://github.com/pytorch/cpuinfo/pull/315.

--- src/freebsd/topology.c.orig
+++ src/freebsd/topology.c
@@ -20,6 +20,7 @@
 	return value;
 }
 
+#if defined(__FreeBSD__)
 static char* sysctl_str(const char* name) {
 	size_t value_size = 0;
 	if (sysctlbyname(name, NULL, &value_size, NULL, 0) != 0) {
@@ -42,6 +43,7 @@
 	}
 	return value;
 }
+#endif
 
 struct cpuinfo_freebsd_topology cpuinfo_freebsd_detect_topology(void) {
 	struct cpuinfo_freebsd_topology topology = {
@@ -50,6 +52,7 @@
 		.threads_per_core = 0,
 		.threads = 0,
 	};
+#if defined (__FreeBSD__)
 	char* topology_spec = sysctl_str("kern.sched.topology_spec");
 	if (!topology_spec) {
 		return topology;
@@ -94,6 +97,19 @@
 		topology.threads_per_core);
 	topology.threads = topology.threads_per_core * topology.cores;
 	return topology;
+#elif defined(__NetBSD__)
+	topology.cores = sysctl_int("hw.ncpu");
+	if (topology.cores == 0) {
+		goto fail;
+	}
+	cpuinfo_log_debug("netbsd topology: cores = %d", topology.cores);
+	/* more details need active identification of the CPU, no sysctl available */
+	/* TODO: improve */
+	topology.threads = topology.cores;
+	topology.packages = 1;
+	topology.threads_per_core = 1;
+	return topology;
+#endif
 fail:
 	topology.packages = 0;
 	return topology;

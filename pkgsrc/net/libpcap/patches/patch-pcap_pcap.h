Preserve native NetBSD build compatibility.
Origin: EmberBSD (AI-assisted); not submitted upstream.

--- pcap/pcap.h.orig
+++ pcap/pcap.h
@@ -128,6 +128,8 @@
 
 #ifndef PCAP_DONT_INCLUDE_PCAP_BPF_H
 #include <pcap/bpf.h>
+#elif defined(__NetBSD__)
+#include <net/bpf.h>
 #endif
 
 #include <stdio.h>

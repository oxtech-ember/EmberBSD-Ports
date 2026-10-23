$NetBSD$

NetBSD libc provides getopt and getopt_long but not the glibc extension
getopt_long_only. The tool does not document single-dash long options,
so use getopt_long.

--- arp-scan.c.orig	2020-04-05 16:12:00.000000000 +0000
+++ arp-scan.c
@@ -1783,7 +1783,7 @@ void process_cmdline(int argc, char *argv[]) {
    int arg;
    int options_index=0;
 
-   while ((arg=getopt_long_only(argc, argv, short_options, long_options, &options_index)) != -1) {
+   while ((arg=getopt_long(argc, argv, short_options, long_options, &options_index)) != -1) {
       switch (arg) {
          struct in_addr source_ip_address;
          int result;

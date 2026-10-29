$NetBSD$

Preserve the SCO host configuration.

--- acinclude.m4.orig
+++ acinclude.m4
@@ -85,6 +85,7 @@
 *-dec-osf*) icu_cv_host_frag=mh-alpha-osf ;;
 *-*-nto*)	icu_cv_host_frag=mh-qnx ;;
 *-ncr-*)	icu_cv_host_frag=mh-mpras ;;
+*-*-sco3.2v5*)	icu_cv_host_frag=mh-scoosr5 ;;
 *-wasi*)	icu_cv_host_frag=mh-wasi ;;
 *) 		icu_cv_host_frag=mh-unknown ;;
 esac

$NetBSD$

Initialize past for writers as well as readers. gzseek64() and gztell64()
read this field in both modes. The unmodified upstream example triggers an
uninitialized branch under Memcheck when it seeks on a compressed writer.
Keep read, write, append, seek and gzip behavior enabled.

Origin: EmberBSD (AI-assisted). Not submitted upstream.

--- gzlib.c.orig
+++ gzlib.c
@@ -68,9 +68,9 @@
 /* Reset gzip file state */
 local void gz_reset(gz_statep state) {
     state->x.have = 0;              /* no output data available */
+    state->past = 0;                /* have not read past end yet */
     if (state->mode == GZ_READ) {   /* for reading ... */
         state->eof = 0;             /* not at end of file */
-        state->past = 0;            /* have not read past end yet */
         state->how = LOOK;          /* look for gzip header */
         state->junk = -1;           /* mark first member */
     }

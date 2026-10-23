$NetBSD$

Use a semaphore wakeup and cooperative join instead of asynchronous thread
cancellation, which can abandon the module's output locks during shutdown.
Check semaphore creation and interrupted waits.
Origin: EmberBSD (AI-assisted).

--- src/modules/dummy.c.orig
+++ src/modules/dummy.c
@@ -28,6 +28,7 @@
 #endif
 
 #include <glib.h>
+#include <errno.h>
 #include <fcntl.h>
 #include <sys/stat.h>
 #include <semaphore.h>
@@ -48,6 +49,7 @@
 static pid_t dummy_pid;
 static sem_t *dummy_semaphore;
 static gboolean initialized = FALSE;
+static gint dummy_closing;
 
 /* Internal functions prototypes */
 static void *_dummy_speak(void *);
@@ -75,12 +77,18 @@
 	char name[64];
 	snprintf(name, sizeof(name), "/speechd-modules-dummy-%d", getpid());
 	dummy_semaphore = sem_open(name, O_CREAT | O_EXCL, S_IRUSR | S_IWUSR, 0);
+	if (dummy_semaphore == SEM_FAILED) {
+		*status_info = g_strdup("Unable to create dummy semaphore");
+		return -1;
+	}
 	sem_unlink(name);
+	g_atomic_int_set(&dummy_closing, FALSE);
 
 	DBG("Dummy: creating new thread for dummy_speak\n");
 	dummy_speaking = 0;
 	ret = spd_pthread_create(&dummy_speak_thread, NULL, _dummy_speak, NULL);
 	if (ret != 0) {
+		sem_close(dummy_semaphore);
 		DBG("Dummy: thread failed\n");
 		*status_info = g_strdup("The module couldn't initialize threads"
 					"This can be either an internal problem or an"
@@ -163,11 +171,14 @@
 	if (!initialized)
 		return 0;
 
+	g_atomic_int_set(&dummy_closing, TRUE);
 	if (dummy_speaking) {
 		module_stop();
 	}
 
-	if (module_terminate_thread(dummy_speak_thread) != 0)
+	/* Wake the worker and join it without cancelling inside output code. */
+	sem_post(dummy_semaphore);
+	if (pthread_join(dummy_speak_thread, NULL) != 0)
 		return -1;
 
 	sem_close(dummy_semaphore);
@@ -184,11 +195,15 @@
 
 	DBG("dummy: speaking thread starting.......\n");
 
-	/* Make interruptible */
-	set_speaking_thread_parameters();
+	/* Shutdown is cooperative: no cancellation while holding output locks. */
 
 	while (1) {
-		sem_wait(dummy_semaphore);
+		int ret;
+		do {
+			ret = sem_wait(dummy_semaphore);
+		} while (ret != 0 && errno == EINTR);
+		if (ret != 0 || g_atomic_int_get(&dummy_closing))
+			break;
 		DBG("Semaphore on\n");
 		module_report_event_begin();
 

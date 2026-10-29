$NetBSD$

Build the upstream keyword generator as a standalone host tool.
Origin: EmberBSD (AI-assisted). Upstream status: not submitted.

--- ntpd/keyword-gen.c.orig
+++ ntpd/keyword-gen.c
@@ -16,21 +16,22 @@
  * the existing source without building anything but a tarball.  See
  * [Bug 1470].
  */
-#include <config.h>
 #include <stdio.h>
 #include <stdlib.h>
 #include <time.h>
 
-#include <ntp_stdlib.h>
-#include <ntp_config.h>
-#include "ntp_scanner.h"
-#include "ntp_parser.h"
+#include <string.h>
+#include "ntp_scanner_types.h"
+#define YYSTYPE int /* Generator uses token IDs, not the parser value union. */
+#include <ntp_parser.h>
+#define COUNTOF(a) ((int)(sizeof(a) / sizeof((a)[0])))
+#define ZERO(x) memset(&(x), 0, sizeof(x))
 
 
 /* Define a structure to hold a (keyword, token) pair */
 struct key_tok {
 	char *	key;		/* Keyword */
-	u_short	token;		/* Associated Token */
+	unsigned short	token;		/* Associated Token */
 	follby	followedby;	/* nonzero indicates the next token(s)
 				   forced to be string(s) */
 };
@@ -265,9 +266,9 @@
 typedef struct big_scan_state_tag {
 	char	ch;		/* Character this state matches on */
 	char	followedby;	/* Forces next token(s) to T_String */
-	u_short	finishes_token;	/* nonzero ID if last keyword char */
-	u_short	match_next_s;	/* next state to check matching ch */
-	u_short	other_next_s;	/* next state to check if not ch */
+	unsigned short	finishes_token;	/* nonzero ID if last keyword char */
+	unsigned short	match_next_s;	/* next state to check matching ch */
+	unsigned short	other_next_s;	/* next state to check if not ch */
 } big_scan_state;
 
 /*
@@ -283,22 +284,20 @@
 
 const char *	current_keyword;/* for error reporting */
 big_scan_state	sst[MAXSTATES];	/* scanner FSM state entries */
-u_short		sst_highwater;	/* next entry index to consider */
+unsigned short		sst_highwater;	/* next entry index to consider */
 char *		symb[1024];	/* map token ID to symbolic name */
 
-/* for libntp */
-const char *	progname = "keyword-gen";
 
 int		main			(int, char **);
 static void	generate_preamble	(void);
 static void	generate_fsm		(void);
 static void	generate_token_text	(void);
-static u_short	create_keyword_scanner	(void);
-static u_short	create_scan_states	(char *, u_short, follby, u_short);
+static unsigned short	create_keyword_scanner	(void);
+static unsigned short	create_scan_states	(char *, unsigned short, follby, unsigned short);
 int		compare_key_tok_id	(const void *, const void *);
 int		compare_key_tok_text	(const void *, const void *);
 void		populate_symb		(char *);
-const char *	symbname		(u_short);
+const char *	symbname		(unsigned short);
 
 
 int main(int argc, char **argv)
@@ -307,7 +306,6 @@
 		fprintf(stderr, "Usage:\n%s t_header.h\n", argv[0]);
 		exit(1);
 	}
-	debug = 1;
 
 	populate_symb(argv[1]);
 
@@ -354,11 +352,11 @@
 	size_t prefix_len;
 	char *p;
 	char *r;
-	u_short initial_state;
-	u_short this_state;
-	u_short state;
-	u_short i;
-	u_short token;
+	unsigned short initial_state;
+	unsigned short this_state;
+	unsigned short state;
+	unsigned short i;
+	unsigned short token;
 
 	/*
 	 * Sort ntp_keywords in alphabetical keyword order.  This is
@@ -516,18 +514,18 @@
  * recognizing the complete keyword, and any pre-existing state that exists
  * for some other keyword that has the same prefix as the current one.
  */
-static u_short
+static unsigned short
 create_scan_states(
 	char *	text,
-	u_short	token,
+	unsigned short	token,
 	follby	followedby,
-	u_short	prev_state
+	unsigned short	prev_state
 	)
 {
-	u_short my_state;
-	u_short return_state;
-	u_short prev_char_s;
-	u_short curr_char_s;
+	unsigned short my_state;
+	unsigned short return_state;
+	unsigned short prev_char_s;
+	unsigned short curr_char_s;
 
 	return_state = prev_state;
 	curr_char_s = prev_state;
@@ -585,10 +583,10 @@
 	 * If not, we need to continue scanning
 	 */
 	if ('\0' == text[1]) {
-		sst[my_state].finishes_token = (u_short)token;
+		sst[my_state].finishes_token = (unsigned short)token;
 		sst[my_state].followedby = (char)followedby;
 
-		if (sst[token].finishes_token != (u_short)token) {
+		if (sst[token].finishes_token != (unsigned short)token) {
 			fprintf(stderr,
 				"fatal, sst[%d] not reserved for %s.\n",
 				token, symbname(token));
@@ -623,11 +621,11 @@
  * creates a keywords scanner out of it.
  */
 
-static u_short
+static unsigned short
 create_keyword_scanner(void)
 {
-	u_short scanner;
-	u_short i;
+	unsigned short scanner;
+	unsigned short i;
 
 	sst_highwater = 1;	/* index 0 invalid, unused */
 	scanner = 0;
@@ -649,11 +647,11 @@
 static void
 generate_token_text(void)
 {
-	u_short lowest_id;
-	u_short highest_id;
-	u_short id_count;
-	u_short id;
-	u_short i;
+	unsigned short lowest_id;
+	unsigned short highest_id;
+	unsigned short id_count;
+	unsigned short id;
+	unsigned short i;
 
 	/* sort ntp_keywords in token ID order */
 	qsort(ntp_keywords, COUNTOF(ntp_keywords),
@@ -745,7 +743,12 @@
 		    && 'T' == name[0] && '_' == name[1] && token >= 0
 		    && token < COUNTOF(symb)) {
 
-			symb[token] = estrdup(name);
+			symb[token] = malloc(strlen(name) + 1);
+			if (symb[token] == NULL) {
+				perror("malloc");
+				exit(1);
+			}
+			strcpy(symb[token], name);
 			if (strlen(name) > MAX_TOK_LEN) {
 				fprintf(stderr,
 					"MAX_TOK_LEN %d too small for '%s'\n"
@@ -760,7 +763,7 @@
 
 const char *
 symbname(
-	u_short token
+	unsigned short token
 	)
 {
 	char *name;
@@ -768,8 +771,9 @@
 	if (token < COUNTOF(symb) && symb[token] != NULL) {
 		name = symb[token];
 	} else {
-		LIB_GETBUF(name);
-		snprintf(name, LIB_BUFLENGTH, "%d", token);
+		static char buffer[32];
+		name = buffer;
+		snprintf(name, sizeof(buffer), "%d", token);
 	}
 
 	return name;
--- ntpd/ntp_scanner.h.orig
+++ ntpd/ntp_scanner.h
@@ -35,12 +35,7 @@
  * non-accepting states (where the state number does not match a T_
  * value).
  */
-typedef enum {
-	FOLLBY_TOKEN = 0,
-	FOLLBY_STRING,
-	FOLLBY_STRINGS_TO_EOC,
-	FOLLBY_NON_ACCEPTING
-} follby;
+#include "ntp_scanner_types.h"
 
 #define MAXLINE		1024	/* maximum length of line */
 #define MAXINCLUDELEVEL	5	/* maximum include file levels */
--- /dev/null
+++ ntpd/ntp_scanner_types.h
@@ -0,0 +1,12 @@
+/* Extracted from ntp_scanner.h; NTP copyright and license apply (see COPYRIGHT). */
+#ifndef NTP_SCANNER_TYPES_H
+#define NTP_SCANNER_TYPES_H
+
+typedef enum {
+	FOLLBY_TOKEN = 0,
+	FOLLBY_STRING,
+	FOLLBY_STRINGS_TO_EOC,
+	FOLLBY_NON_ACCEPTING
+} follby;
+
+#endif /* NTP_SCANNER_TYPES_H */

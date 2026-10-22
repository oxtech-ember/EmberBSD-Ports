/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD contributors (AI-assisted). */
#include <gssapi/gssapi.h>
#include <gssapi/gssapi_krb5.h>
#include <krb5.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static void
check(int condition, const char *message)
{
	if (!condition) {
		fprintf(stderr, "FAIL: %s\n", message);
		exit(1);
	}
}

static void
check_client_keytab_default(void)
{
	krb5_context context = NULL;
	krb5_keytab keytab = NULL;
	const char *statedir = getenv("KRB5_TEST_CLIENT_KT_STATEDIR");
	char expected[4096];
	char actual[4096];
	int length;

	check(getenv("KRB5_CONFIG") != NULL, "bundled KRB5_CONFIG is set");
	check(getenv("KRB5_CLIENT_KTNAME") == NULL,
	    "KRB5_CLIENT_KTNAME is unset for default lookup");
	if (statedir == NULL || statedir[0] != '/') {
		check(0, "target client keytab statedir is absolute");
		return;
	}
	length = snprintf(expected, sizeof(expected),
	    "FILE:%s/krb5/user/%lu/client.keytab", statedir,
	    (unsigned long)geteuid());
	check(length >= 0 && (size_t)length < sizeof(expected),
	    "target client keytab expectation fits");
	check(krb5_init_context(&context) == 0,
	    "initialize context for client keytab default");
	check(krb5_kt_client_default(context, &keytab) == 0,
	    "resolve default client keytab");
	check(krb5_kt_get_name(context, keytab, actual, sizeof(actual)) == 0 &&
	    strcmp(actual, expected) == 0,
	    "default client keytab uses the target statedir");
	check(krb5_kt_close(context, keytab) == 0,
	    "close resolved default client keytab");
	krb5_free_context(context);
}

static void *
worker(void *unused)
{
	krb5_context ctx = NULL;
	krb5_principal principal = NULL, copied = NULL;
	krb5_ccache cache = NULL;
	krb5_data data = { 0 };
	krb5_keyblock key = { 0 };
	krb5_enc_data encrypted = { 0 };
	char *name = NULL;
	char cleartext[32] = "GUI printing GSS client";
	char plaintext[32];
	unsigned int i;
	size_t ciphertext_size;
	(void)unused;

	check(krb5_init_context(&ctx) == 0, "krb5_init_context");
	check(krb5_parse_name(ctx, "gui/print.example@EXAMPLE.INVALID", &principal) == 0,
	    "parse explicit principal");
	check(krb5_copy_principal(ctx, principal, &copied) == 0 &&
	    krb5_principal_compare(ctx, principal, copied), "principal copy");
	check(krb5_unparse_name(ctx, copied, &name) == 0 &&
	    strcmp(name, "gui/print.example@EXAMPLE.INVALID") == 0, "principal round trip");
	krb5_free_unparsed_name(ctx, name);
	check(krb5_cc_new_unique(ctx, "MEMORY", NULL, &cache) == 0 &&
	    krb5_cc_initialize(ctx, cache, principal) == 0, "memory credential cache");
	check(krb5_cc_destroy(ctx, cache) == 0, "destroy memory credential cache");
	check(krb5_c_make_random_key(ctx, ENCTYPE_AES256_CTS_HMAC_SHA1_96, &key) == 0,
	    "AES256 random key");
	data.data = cleartext;
	data.length = (unsigned int)strlen(cleartext);
	check(krb5_c_encrypt_length(ctx, key.enctype, data.length, &ciphertext_size) == 0,
	    "AES256 ciphertext size");
	check(ciphertext_size <= 256, "bounded ciphertext size");
	encrypted.ciphertext.data = malloc(ciphertext_size);
	check(encrypted.ciphertext.data != NULL, "ciphertext allocation");
	encrypted.ciphertext.length = (unsigned int)ciphertext_size;
	check(krb5_c_encrypt(ctx, &key, 42, NULL, &data, &encrypted) == 0,
	    "AES256 encryption");
	data.data = plaintext;
	data.length = sizeof(plaintext);
	check(krb5_c_decrypt(ctx, &key, 42, NULL, &encrypted, &data) == 0 &&
	    data.length == strlen(cleartext) && memcmp(data.data, cleartext, data.length) == 0,
	    "AES256 decryption");
	for (i = 0; i < encrypted.ciphertext.length; i++)
		encrypted.ciphertext.data[i] ^= 1;
	data.length = sizeof(plaintext);
	check(krb5_c_decrypt(ctx, &key, 42, NULL, &encrypted, &data) != 0,
	    "modified ciphertext rejected");
	free(encrypted.ciphertext.data);
	krb5_free_keyblock_contents(ctx, &key);
	krb5_free_principal(ctx, copied);
	krb5_free_principal(ctx, principal);
	krb5_free_context(ctx);
	return NULL;
}

int
main(void)
{
	pthread_t threads[4];
	gss_OID_set mechs = GSS_C_NO_OID_SET;
	gss_name_t name = GSS_C_NO_NAME;
	gss_buffer_desc input = { 0, "printer@print.example.org" };
	gss_buffer_desc output = GSS_C_EMPTY_BUFFER;
	OM_uint32 major, minor;
	int present = 0;
	size_t i;

	check_client_keytab_default();
	check(krb5_is_thread_safe() != 0, "installed MIT client is thread safe");
	for (i = 0; i < 4; i++)
		check(pthread_create(&threads[i], NULL, worker, NULL) == 0, "pthread_create");
	for (i = 0; i < 4; i++)
		check(pthread_join(threads[i], NULL) == 0, "pthread_join");
	major = gss_indicate_mechs(&minor, &mechs);
	check(major == GSS_S_COMPLETE, "enumerate installed GSS mechanisms");
	check(gss_test_oid_set_member(&minor, gss_mech_krb5, mechs, &present) ==
	    GSS_S_COMPLETE && present, "MIT Kerberos GSS mechanism");
	check(gss_release_oid_set(&minor, &mechs) == GSS_S_COMPLETE, "release GSS mechanisms");
	input.length = strlen(input.value);
	check(gss_import_name(&minor, &input, GSS_C_NT_HOSTBASED_SERVICE, &name) ==
	    GSS_S_COMPLETE, "import GSS service name");
	check(gss_display_name(&minor, name, &output, NULL) == GSS_S_COMPLETE &&
	    output.length == input.length && memcmp(output.value, input.value, input.length) == 0,
	    "display GSS service name");
	check(gss_release_buffer(&minor, &output) == GSS_S_COMPLETE, "release GSS name buffer");
	check(gss_release_name(&minor, &name) == GSS_S_COMPLETE, "release GSS name");
	puts("PASS: target client keytab default; thread-safe MIT Kerberos/GSS "
	    "APIs and concurrent cache/AES lifecycles");
	return 0;
}

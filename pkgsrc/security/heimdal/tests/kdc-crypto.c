#include <openssl/evp.h>
#include <openssl/hmac.h>
#include <openssl/provider.h>
#include <openssl/sha.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef void *krb5_context;
typedef int krb5_error_code;
typedef struct {
	size_t length;
	void *data;
} krb5_data;
typedef struct {
	krb5_data keyvalue;
} krb5_keyblock;
typedef struct {
	krb5_data pk_hash, pk_key;
} Kx509Request;
typedef struct {
	int32_t *error_code;
	krb5_data *certificate, *hash;
	char **e_text;
} Kx509Response;
#define KRB5KDC_ERR_PREAUTH_FAILED 44
#define HEIMDAL_OPAQUE_HMAC 1
#define HEIMDAL_OPAQUE_EVP 1
static int fail_hmac_alloc, fail_update, fail_evp_alloc, fail_cipher, wipes;
static int hmac_allocs, hmac_frees, evp_allocs, evp_frees, check_hash_wipe,
    hash_wiped;
static int
krb5_enomem(krb5_context c)
{
	(void)c;
	return ENOMEM;
}
static void
krb5_set_error_message(krb5_context c, int e, const char *fmt, ...)
{
	(void)c;
	(void)e;
	(void)fmt;
}
static int
krb5_data_alloc(krb5_data *d, size_t n)
{
	d->data = calloc(1, n);
	d->length = d->data ? n : 0;
	return d->data ? 0 : ENOMEM;
}
static void
krb5_data_free(krb5_data *d)
{
	if (check_hash_wipe && d->data) {
		const unsigned char *p = d->data;
		int zero = 1;
		for (size_t i = 0; i < d->length; i++)
			zero &= p[i] == 0;
		hash_wiped = zero;
	}
	free(d->data);
	d->data = NULL;
	d->length = 0;
}
static int
memset_s(void *p, size_t n, int v, size_t l)
{
	(void)n;
	wipes++;
	memset(p, v, l);
	return 0;
}
static HMAC_CTX *
test_hmac_new(void)
{
	HMAC_CTX *p = fail_hmac_alloc ? NULL : HMAC_CTX_new();
	if (p)
		hmac_allocs++;
	return p;
}
static void
test_hmac_free(HMAC_CTX *p)
{
	if (p)
		hmac_frees++;
	HMAC_CTX_free(p);
}
static int
test_hmac_update(HMAC_CTX *c, const unsigned char *p, size_t n)
{
	return fail_update ? 0 : HMAC_Update(c, p, n);
}
static EVP_CIPHER_CTX *
test_evp_new(void)
{
	EVP_CIPHER_CTX *p = fail_evp_alloc ? NULL : EVP_CIPHER_CTX_new();
	if (p)
		evp_allocs++;
	return p;
}
static void
test_evp_free(EVP_CIPHER_CTX *p)
{
	if (p)
		evp_frees++;
	EVP_CIPHER_CTX_free(p);
}
static int
test_cipher(EVP_CIPHER_CTX *c, unsigned char *o, const unsigned char *i,
	    unsigned int n)
{
	if (fail_cipher) {
		memset(o, 0xa5, n);
		return 0;
	}
	return EVP_Cipher(c, o, i, n);
}
#define HMAC_CTX_new test_hmac_new
#define HMAC_CTX_free test_hmac_free
#define HMAC_Update test_hmac_update
#define EVP_CIPHER_CTX_new test_evp_new
#define EVP_CIPHER_CTX_free test_evp_free
#define EVP_Cipher test_cipher
#define KX509_HMAC_OK(call) ((call) == 1)
#define KX509_HMAC_FREE(ctx) HMAC_CTX_free(ctx)
#include "kx509.inc"
#include "digest.inc"
int
main(void)
{
	OSSL_PROVIDER *def = OSSL_PROVIDER_load(NULL, "default"),
		      *legacy = OSSL_PROVIDER_load(NULL, "legacy");
	unsigned char keybytes[16] = {0}, payload[] = {1, 2, 3}, expected[20],
		      actual[16], cipher[16];
	unsigned int n = 0;
	unsigned char message[] = {0, 0, 2, 0, 1, 2, 3};
	krb5_keyblock key = {{sizeof(keybytes), keybytes}};
	Kx509Request req = {{20, expected}, {sizeof(payload), payload}};
	krb5_data hash = {0}, cert = {sizeof(payload), payload};
	Kx509Response rep = {NULL, &cert, &hash, NULL};
	if (!def || !legacy ||
	    !HMAC(EVP_sha1(), keybytes, sizeof keybytes, message,
		  sizeof message, expected, &n) ||
	    n != 20)
		return 1;
	if (verify_req_hash(NULL, &req, &key) ||
	    calculate_reply_hash(NULL, &key, &rep) || hash.length != 20 ||
	    memcmp(hash.data, expected, 20))
		return 2;
	krb5_data_free(&hash);
	fail_update = 1;
	wipes = 0;
	check_hash_wipe = 1;
	if (verify_req_hash(NULL, &req, &key) != EINVAL ||
	    calculate_reply_hash(NULL, &key, &rep) != EINVAL || hash.data ||
	    hash.length || wipes < 2 || !hash_wiped)
		return 3;
	check_hash_wipe = 0;
	fail_update = 0;
	fail_hmac_alloc = 1;
	if (verify_req_hash(NULL, &req, &key) != ENOMEM ||
	    calculate_reply_hash(NULL, &key, &rep) != ENOMEM)
		return 4;
	fail_hmac_alloc = 0;
	for (int i = 0; i < 16; i++)
		cipher[i] = (unsigned char)i;
	if (ntlm_unwrap_sessionkey(NULL, keybytes, cipher, actual, 16))
		return 5;
	unsigned char roundtrip[16];
	if (ntlm_unwrap_sessionkey(NULL, keybytes, actual, roundtrip, 16) ||
	    memcmp(roundtrip, cipher, 16))
		return 6;
	fail_evp_alloc = 1;
	memset(actual, 0xa5, 16);
	if (ntlm_unwrap_sessionkey(NULL, keybytes, cipher, actual, 16) !=
	    ENOMEM)
		return 7;
	for (int i = 0; i < 16; i++)
		if (actual[i])
			return 8;
	fail_evp_alloc = 0;
	fail_cipher = 1;
	memset(actual, 0xa5, 16);
	if (ntlm_unwrap_sessionkey(NULL, keybytes, cipher, actual, 16) !=
	    EINVAL)
		return 9;
	for (int i = 0; i < 16; i++)
		if (actual[i])
			return 10;
	if (hmac_allocs != hmac_frees || evp_allocs != evp_frees)
		return 11;
	OSSL_PROVIDER_unload(legacy);
	OSSL_PROVIDER_unload(def);
	puts("KDC HMAC/RC4 valid inputs and failures PASS");
	return 0;
}

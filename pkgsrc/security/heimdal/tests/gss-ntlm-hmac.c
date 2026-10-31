#include <openssl/evp.h>
#include <openssl/hmac.h>
#include <openssl/provider.h>
#include <openssl/rc4.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint32_t OM_uint32;
typedef struct {
	size_t length;
	void *value;
} gss_buffer_desc, *gss_buffer_t;
#define GSS_S_COMPLETE 0
#define GSS_S_FAILURE 851968
#define GSS_S_BAD_MIC 393216
#define GSS_S_UNAVAILABLE 1048576
#define GSSAPI_CALLCONV
#define NTLM_NEG_SIGN 1
#define NTLM_NEG_NTLM2_SESSION 2
#define NTLM_NEG_ALWAYS_SIGN 4
#define STATUS_SESSIONKEY 1
#define CTX_FLAGS_ISSET(c, f) (((c)->flags & (f)) == (f))
typedef const void *gss_const_ctx_id_t;
typedef unsigned int gss_qop_t;
typedef struct ntlm_ctx_data {
	unsigned int flags, status;
	struct {
		struct {
			struct {
				unsigned char signkey[16];
				RC4_KEY *signsealkey;
				uint32_t seq;
			} send;
		} v2;
		struct {
			struct {
				RC4_KEY key;
				uint32_t seq;
			} crypto_send;
		} v1;
	} u;
} *ntlm_ctx;
#define HEIMNTLM_GSS_OPAQUE_HMAC 1
static int fail_alloc, fail_update;
static int
memset_s(void *p, size_t n, int v, size_t len)
{
	(void)n;
	memset(p, v, len);
	return 0;
}
static HMAC_CTX *
test_new(void)
{
	return fail_alloc ? NULL : HMAC_CTX_new();
}
static int
test_update(HMAC_CTX *c, const unsigned char *p, size_t n)
{
	return fail_update ? 0 : HMAC_Update(c, p, n);
}
static void
gss_release_buffer(OM_uint32 *minor, gss_buffer_t b)
{
	*minor = 0;
	free(b->value);
	b->value = NULL;
	b->length = 0;
}
#define HMAC_CTX_new test_new
#define HMAC_Update test_update
#include "functions.inc"
static OM_uint32
v1_sign_message(gss_buffer_t in, RC4_KEY *key, uint32_t seq,
		unsigned char out[16])
{
	(void)in;
	(void)key;
	(void)seq;
	(void)out;
	return GSS_S_FAILURE;
}
#include "get-mic.inc"
int
main(void)
{
	OSSL_PROVIDER *p = OSSL_PROVIDER_load(NULL, "default");
	unsigned char key[16] = {0}, msg[] = {1, 2, 3, 4}, out[16],
		      expected[16];
	unsigned char hmsg[] = {42, 0, 0, 0, 1, 2, 3, 4};
	unsigned int hlen = 0;
	gss_buffer_desc in = {sizeof(msg), msg}, sealed = {0}, opened = {0};
	RC4_KEY enc, dec, before;
	if (!p ||
	    !HMAC(EVP_md5(), key, 16, hmsg, sizeof(hmsg), expected, &hlen) ||
	    hlen != 16)
		return 1;
	if (v2_sign_message(&in, key, NULL, 42, out) ||
	    memcmp(out + 4, expected, 8))
		return 2;
	RC4_set_key(&enc, 16, key);
	RC4_set_key(&dec, 16, key);
	if (v2_seal_message(&in, key, 42, &enc, &sealed) ||
	    v2_unseal_message(&sealed, key, 42, &dec, &opened) ||
	    opened.length != sizeof(msg) ||
	    memcmp(opened.value, msg, sizeof(msg)))
		return 3;
	OM_uint32 junk;
	gss_release_buffer(&junk, &opened);
	gss_release_buffer(&junk, &sealed);
	RC4_set_key(&enc, 16, key);
	before = enc;
	fail_alloc = 1;
	if (v2_seal_message(&in, key, 42, &enc, &sealed) != GSS_S_FAILURE ||
	    memcmp(&enc, &before, sizeof enc))
		return 4;
	fail_alloc = 0;
	if (v2_seal_message(&in, key, 42, &enc, &sealed))
		return 5;
	RC4_set_key(&dec, 16, key);
	before = dec;
	fail_update = 1;
	if (v2_unseal_message(&sealed, key, 42, &dec, &opened) !=
		GSS_S_FAILURE ||
	    memcmp(&dec, &before, sizeof dec) || opened.value != NULL)
		return 6;
	fail_update = 0;
	if (v2_unseal_message(&sealed, key, 42, &dec, &opened) ||
	    opened.length != sizeof(msg) ||
	    memcmp(opened.value, msg, sizeof(msg)))
		return 7;
	gss_release_buffer(&junk, &opened);
	gss_release_buffer(&junk, &sealed);
	struct ntlm_ctx_data context = {0};
	context.flags = NTLM_NEG_SIGN | NTLM_NEG_NTLM2_SESSION;
	context.status = STATUS_SESSIONKEY;
	context.u.v2.send.seq = 42;
	gss_buffer_desc token = {0};
	fail_alloc = 1;
	if (_gss_ntlm_get_mic(&junk, &context, 0, &in, &token) !=
		GSS_S_FAILURE ||
	    context.u.v2.send.seq != 42 || token.value)
		return 8;
	fail_alloc = 0;
	if (_gss_ntlm_get_mic(&junk, &context, 0, &in, &token) !=
		GSS_S_COMPLETE ||
	    context.u.v2.send.seq != 43 || token.length != 16)
		return 9;
	gss_release_buffer(&junk, &token);
	OSSL_PROVIDER_unload(p);
	puts("GSS NTLM valid MIC/seal and failure state retry PASS");
	return 0;
}

/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD contributors (AI-assisted). */
#include <arpa/inet.h>
#include <openssl/ssl.h>
#include <openssl/x509v3.h>
#include <stdio.h>
#include <string.h>
#include "peername.inc"

#define CHECK(test) do { if (!(test)) { \
	fprintf(stderr, "FAIL at line %d\n", __LINE__); return 1; \
} } while (0)

static int
verify(SSL_CTX *context, X509 *cert, const char *host, int expected)
{
	SSL *ssl = SSL_new(context);
	X509_STORE *store = X509_STORE_new();
	X509_STORE_CTX *check = X509_STORE_CTX_new();
	int result = 1;

	if (ssl == NULL || store == NULL || check == NULL)
		goto done;
	if (!fetch_ssl_set_peername(ssl, host) ||
	    !SSL_set_tlsext_host_name(ssl, host) ||
	    strcmp(SSL_get_servername(ssl, TLSEXT_NAMETYPE_host_name), host) ||
	    !X509_STORE_add_cert(store, cert) ||
	    !X509_STORE_CTX_init(check, store, cert, NULL) ||
	    !X509_VERIFY_PARAM_inherit(X509_STORE_CTX_get0_param(check),
	    SSL_get0_param(ssl)))
		goto done;
	result = (X509_verify_cert(check) == 1) != expected;
	done:
	X509_STORE_CTX_free(check);
	X509_STORE_free(store);
	SSL_free(ssl);
	return result;
}

int
main(void)
{
	EVP_PKEY *key = EVP_EC_gen("prime256v1");
	X509 *cert = X509_new();
	X509_NAME *name;
	X509_EXTENSION *san;
	SSL_CTX *context = SSL_CTX_new(TLS_client_method());
	SSL *ssl;
	CHECK(key != NULL && cert != NULL && context != NULL);
	CHECK(X509_set_version(cert, 2));
	CHECK(ASN1_INTEGER_set(X509_get_serialNumber(cert), 1));
	CHECK(X509_gmtime_adj(X509_getm_notBefore(cert), -60) != NULL);
	CHECK(X509_gmtime_adj(X509_getm_notAfter(cert), 3600) != NULL);
	CHECK(X509_set_pubkey(cert, key));
	name = X509_NAME_new();
	CHECK(name != NULL);
	CHECK(X509_NAME_add_entry_by_txt(name, "CN", MBSTRING_ASC,
	    (const unsigned char *)"peer.example", -1, -1, 0));
	CHECK(X509_set_subject_name(cert, name));
	CHECK(X509_set_issuer_name(cert, name));
	X509_NAME_free(name);
	san = X509V3_EXT_conf_nid(NULL, NULL, NID_subject_alt_name,
	    "DNS:peer.example,DNS:192.0.2.2,IP:192.0.2.1,IP:2001:db8::1");
	CHECK(san != NULL && X509_add_ext(cert, san, -1));
	X509_EXTENSION_free(san);
	CHECK(X509_sign(cert, key, EVP_sha256()) > 0);
	CHECK(verify(context, cert, "peer.example", 1) == 0);
	CHECK(verify(context, cert, "wrong.example", 0) == 0);
	CHECK(verify(context, cert, "192.0.2.1", 1) == 0);
	CHECK(verify(context, cert, "192.000.002.001", 0) == 0);
	/* A numeric DNS SAN must not satisfy an IP reference identifier. */
	CHECK(verify(context, cert, "192.0.2.2", 0) == 0);
	CHECK(verify(context, cert, "2001:db8::1", 1) == 0);
	CHECK(verify(context, cert, "2001:db8::2", 0) == 0);
	ssl = SSL_new(context);
	CHECK(ssl != NULL);
	CHECK(fetch_ssl_set_peername(ssl, NULL) == 0);
	CHECK(fetch_ssl_set_peername(ssl, "") == 0);
	SSL_free(ssl);
	SSL_CTX_free(context);
	X509_free(cert);
	EVP_PKEY_free(key);
	puts("PASS: libfetch DNS, IPv4, IPv6, mismatch, SNI and empty-name cases");
	return 0;
}

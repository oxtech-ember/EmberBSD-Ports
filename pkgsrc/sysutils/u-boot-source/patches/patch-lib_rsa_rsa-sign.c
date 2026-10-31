$NetBSD$

--- a/lib/rsa/rsa-sign.c
+++ b/lib/rsa/rsa-sign.c
@@ -19,7 +19,19 @@
 #include <openssl/err.h>
 #include <openssl/ssl.h>
 #include <openssl/evp.h>
+#include <openssl/opensslv.h>
+#if OPENSSL_VERSION_MAJOR >= 4
+#include <openssl/provider.h>
+#include <openssl/store.h>
+#include <openssl/ui.h>
+typedef struct {
+	OSSL_PROVIDER *provider;
+	char *id;
+} RSA_KEY_PROVIDER;
+#define ENGINE RSA_KEY_PROVIDER
+#else
 #include <openssl/engine.h>
+#endif
 
 static int rsa_err(const char *msg)
 {
@@ -89,6 +101,7 @@
 	return ret;
 }
 
+#if OPENSSL_VERSION_MAJOR < 4
 /**
  * rsa_engine_get_pub_key() - read a public key from given engine
  *
@@ -158,6 +171,10 @@
 	return 0;
 }
 
+#else
+static int rsa_engine_get_pub_key(const char *, const char *, ENGINE *, EVP_PKEY **);
+#endif
+
 /**
  * rsa_get_pub_key() - read a public key
  *
@@ -217,6 +234,7 @@
 	return 0;
 }
 
+#if OPENSSL_VERSION_MAJOR < 4
 /**
  * rsa_engine_get_priv_key() - read a private key from given engine
  *
@@ -294,6 +312,10 @@
 	return 0;
 }
 
+#else
+static int rsa_engine_get_priv_key(const char *, const char *, const char *, ENGINE *, EVP_PKEY **);
+#endif
+
 /**
  * rsa_get_priv_key() - read a private key
  *
@@ -325,6 +347,7 @@
 	return 0;
 }
 
+#if OPENSSL_VERSION_MAJOR < 4
 static int rsa_engine_init(const char *engine_id, ENGINE **pe)
 {
 	const char *key_pass;
@@ -380,6 +403,154 @@
 		ENGINE_free(e);
 	}
 }
+
+#else
+/* OpenSSL 4 removed engines. A provider is selected by the former engine
+ * identifier, and its keys are addressed by the provider's STORE URI. */
+static int rsa_engine_init(const char *id, ENGINE **out)
+{
+	ENGINE *e = calloc(1, sizeof(*e));
+
+	if (!e)
+		return -ENOMEM;
+	e->id = strdup(id);
+	if (!e->id)
+		goto fail;
+	/* Loading a non-default provider suppresses implicit default loading. */
+	if (!OSSL_PROVIDER_available(NULL, "default") &&
+	    !OSSL_PROVIDER_load(NULL, "default"))
+		goto fail;
+	e->provider = OSSL_PROVIDER_load(NULL, id);
+	if (!e->provider)
+		goto fail;
+	*out = e;
+	return 0;
+fail:
+	fprintf(stderr, "Unable to load OpenSSL provider '%s'\n", id);
+	ERR_print_errors_fp(stderr);
+	free(e->id);
+	free(e);
+	return -1;
+}
+
+static void rsa_engine_remove(ENGINE *e)
+{
+	if (e) {
+		OSSL_PROVIDER_unload(e->provider);
+		free(e->id);
+		free(e);
+	}
+}
+
+static int rsa_pin_cb(char *buf, int size, int rwflag, void *userdata)
+{
+	const char *pin = userdata;
+	size_t len;
+
+	(void)rwflag;
+	if (!pin)
+		return 0;
+	len = strlen(pin);
+	if (len >= (size_t)size)
+		return 0;
+	memcpy(buf, pin, len);
+	return len;
+}
+
+static int rsa_store_key(const char *keydir, const char *name,
+			 const char *keyfile, ENGINE *e, bool private,
+			 EVP_PKEY **out)
+{
+	char uri[1024];
+	const char *pin = getenv("MKIMAGE_SIGN_PIN");
+	UI_METHOD *ui = NULL;
+	OSSL_STORE_CTX *ctx = NULL;
+	OSSL_STORE_INFO *item = NULL;
+	int len, ret = -1;
+
+	if (!out)
+		return -EINVAL;
+	*out = NULL;
+	if (!strcmp(e->id, "pkcs11")) {
+		const char *prefix = keydir && strncmp(keydir, "pkcs11:", 7) ? "pkcs11:" : "";
+		if (keydir && (strstr(keydir, "object=") || strstr(keydir, "id=")))
+			len = snprintf(uri, sizeof(uri), "%s%s;type=%s", prefix, keydir,
+				       private ? "private" : "public");
+		else if (name)
+			len = snprintf(uri, sizeof(uri), "%s%s%sobject=%s;type=%s",
+				       keydir ? prefix : "pkcs11:", keydir ? keydir : "",
+				       keydir ? ";" : "", name, private ? "private" : "public");
+		else
+			return -EINVAL;
+	} else if (private && keyfile) {
+		len = snprintf(uri, sizeof(uri), "%s", keyfile);
+	} else if (keydir && name) {
+		len = snprintf(uri, sizeof(uri), "%s%s", keydir, name);
+	} else if (name || keyfile) {
+		len = snprintf(uri, sizeof(uri), "%s", name ? name : keyfile);
+	} else {
+		return -EINVAL;
+	}
+	if (len < 0 || (size_t)len >= sizeof(uri))
+		return -ENAMETOOLONG;
+	if (pin) {
+		ui = UI_UTIL_wrap_read_pem_callback(rsa_pin_cb, 0);
+		if (!ui)
+			goto done;
+	}
+	ctx = OSSL_STORE_open(uri, ui, (void *)pin, NULL, NULL);
+	if (!ctx)
+		goto done;
+	while (!OSSL_STORE_eof(ctx)) {
+		item = OSSL_STORE_load(ctx);
+		if (!item) {
+			if (OSSL_STORE_error(ctx))
+				break;
+			continue;
+		}
+		if (private && OSSL_STORE_INFO_get_type(item) == OSSL_STORE_INFO_PKEY)
+			*out = OSSL_STORE_INFO_get1_PKEY(item);
+		else if (!private && OSSL_STORE_INFO_get_type(item) == OSSL_STORE_INFO_PUBKEY)
+			*out = OSSL_STORE_INFO_get1_PUBKEY(item);
+		else if (!private && OSSL_STORE_INFO_get_type(item) == OSSL_STORE_INFO_PKEY)
+			*out = OSSL_STORE_INFO_get1_PKEY(item);
+		else if (!private && OSSL_STORE_INFO_get_type(item) == OSSL_STORE_INFO_CERT) {
+			X509 *cert = OSSL_STORE_INFO_get1_CERT(item);
+			if (cert) {
+				*out = X509_get_pubkey(cert);
+				X509_free(cert);
+			}
+		}
+		OSSL_STORE_INFO_free(item);
+		item = NULL;
+		if (*out) {
+			ret = 0;
+			break;
+		}
+	}
+done:
+	if (ret) {
+		fprintf(stderr, "Unable to load RSA key from provider\n");
+		ERR_print_errors_fp(stderr);
+	}
+	if (ctx)
+		OSSL_STORE_close(ctx);
+	UI_destroy_method(ui);
+	return ret;
+}
+
+static int rsa_engine_get_pub_key(const char *dir, const char *name,
+				  ENGINE *e, EVP_PKEY **out)
+{
+	return rsa_store_key(dir, name, NULL, e, false, out);
+}
+
+static int rsa_engine_get_priv_key(const char *dir, const char *name,
+				   const char *file, ENGINE *e, EVP_PKEY **out)
+{
+	return rsa_store_key(dir, name, file, e, true, out);
+}
+#endif
 
 static int rsa_sign_with_key(EVP_PKEY *pkey, struct padding_algo *padding_algo,
 			     struct checksum_algo *checksum_algo,
@@ -655,6 +826,10 @@
 		goto err_get_pub_key;
 
 	rsa = (RSA *)EVP_PKEY_get0_RSA(pkey);
+	if (!rsa) {
+		ret = rsa_err("Provider key does not expose RSA parameters");
+		goto err_get_params;
+	}
 	ret = rsa_get_params(rsa, &exponent, &n0_inv, &modulus, &r_squared);
 	if (ret)
 		goto err_get_params;

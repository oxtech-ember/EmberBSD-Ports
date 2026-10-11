/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Offline checks of Qt's network providers. */
#include <curl/curl.h>
#include <idn2.h>
#include <locale.h>
#include <stdio.h>
#include <string.h>

int
main(void)
{
	const curl_version_info_data *version;
	CURLU *url = NULL;
	char *host = NULL, *escaped = NULL;
	uint8_t *ascii = NULL;
	int result = 1;

	/* libcurl's libidn2 backend uses the process locale for host names. */
	if (setlocale(LC_CTYPE, "C.UTF-8") == NULL) {
		fprintf(stderr, "C.UTF-8 locale is required\n");
		return 1;
	}
	if (curl_global_init(CURL_GLOBAL_DEFAULT) != CURLE_OK)
		return 1;
	version = curl_version_info(CURLVERSION_NOW);
	if (strcmp(version->version, "8.22.0") != 0 ||
	    strcmp(idn2_check_version(NULL), "2.3.8") != 0 ||
	    (version->features & (CURL_VERSION_SSL | CURL_VERSION_IDN |
	    CURL_VERSION_HTTP2)) != (CURL_VERSION_SSL | CURL_VERSION_IDN |
	    CURL_VERSION_HTTP2))
		goto out;
	result = 2;
	if (idn2_lookup_u8((const uint8_t *)"b\303\274cher.example", &ascii,
	    IDN2_NFC_INPUT) != IDN2_OK || ascii == NULL ||
	    strcmp((const char *)ascii, "xn--bcher-kva.example") != 0)
		goto out;
	result = 3;
	url = curl_url();
	if (url == NULL || curl_url_set(url, CURLUPART_URL,
	    "https://b\303\274cher.example/", 0) != CURLUE_OK ||
	    curl_url_get(url, CURLUPART_HOST, &host, CURLU_PUNYCODE) != CURLUE_OK ||
	    strcmp(host, "xn--bcher-kva.example") != 0)
		goto out;
	result = 4;
	if (curl_url_set(url, CURLUPART_URL, "https://[invalid/", 0) == CURLUE_OK)
		goto out;
	result = 5;
	escaped = curl_easy_escape(NULL, "Ember GPU + Qt", 0);
	if (escaped == NULL || strcmp(escaped, "Ember%20GPU%20%2B%20Qt") != 0)
		goto out;
	printf("PASS: curl %s, libidn2 %s, IDN URL, escaping and invalid URL rejection\n",
	    version->version, idn2_check_version(NULL));
	result = 0;
out:
	if (result != 0)
		fprintf(stderr, "FAIL stage %d: curl=%s, idn=%s, features=%x\n",
		    result, version->version, idn2_check_version(NULL), version->features);
	curl_free(escaped);
	curl_free(host);
	curl_url_cleanup(url);
	idn2_free(ascii);
	curl_global_cleanup();
	return result;
}

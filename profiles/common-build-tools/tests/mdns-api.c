/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted), bounded real DNS-SD public API contract. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <dns_sd.h>

_Static_assert(_DNS_SD_H == 16610000, "The pinned release's public API version changed");
_Static_assert(sizeof(TXTRecordRef) == 16, "The public TXT record ABI changed");

int
main(void)
{
	unsigned char bytes[252];
	unsigned cases = 0;
	char fullname[kDNSServiceMaxDomainName];
	for (unsigned i = 0; i < sizeof(bytes); i++)
		bytes[i] = (unsigned char)(i * 73);
	for (unsigned storage = 0; storage < 2; storage++) {
		unsigned char small[8];
		TXTRecordRef record;
		TXTRecordCreate(&record, storage ? sizeof(small) : 0,
		    storage ? small : NULL);
		assert(TXTRecordGetLength(&record) == 0);
		/* The length octet counts key, '=' and value: 3 + 1 + 250. */
		for (unsigned n = 0; n <= 250; n++) {
			uint8_t length;
			const void *value, *indexed;
			char key[4];
			assert(TXTRecordSetValue(&record, "bin", n, bytes) == kDNSServiceErr_NoError);
			uint16_t size = TXTRecordGetLength(&record);
			const void *raw = TXTRecordGetBytesPtr(&record);
			assert(size == n + 5);
			assert(TXTRecordGetCount(size, raw) == 1);
			assert(TXTRecordContainsKey(size, raw, "BIN"));
			value = TXTRecordGetValuePtr(size, raw, "bin", &length);
			assert(value != NULL && length == n && memcmp(value, bytes, n) == 0);
			assert(TXTRecordGetItemAtIndex(size, raw, 0, sizeof(key), key,
			    &length, &indexed) == kDNSServiceErr_NoError);
			assert(strcmp(key, "bin") == 0 && length == n && memcmp(indexed, bytes, n) == 0);
			cases++;
		}
		assert(TXTRecordSetValue(&record, "bin", 251, bytes) == kDNSServiceErr_Invalid);
		assert(TXTRecordSetValue(&record, "a=b", 0, NULL) == kDNSServiceErr_Invalid);
		assert(TXTRecordSetValue(&record, "", 0, NULL) == kDNSServiceErr_Invalid);
		assert(TXTRecordGetLength(&record) == 255);
		assert(TXTRecordRemoveValue(&record, "BIN") == kDNSServiceErr_NoError);
		assert(TXTRecordGetLength(&record) == 0);
		assert(TXTRecordRemoveValue(&record, "absent") == kDNSServiceErr_NoSuchKey);
		assert(TXTRecordSetValue(&record, "flag", 0, NULL) == kDNSServiceErr_NoError);
		assert(TXTRecordContainsKey(TXTRecordGetLength(&record), TXTRecordGetBytesPtr(&record), "flag"));
		TXTRecordDeallocate(&record);
		cases += 7;
	}
	assert(DNSServiceConstructFullName(fullname, "Lab.Printer", "_ipp._tcp", "local.") == kDNSServiceErr_NoError);
	assert(strcmp(fullname, "Lab\\.Printer._ipp._tcp.local.") == 0);
	assert(DNSServiceBrowse(NULL, 0, 0, "_ipp._tcp", NULL, NULL, NULL) == kDNSServiceErr_BadParam);
	cases += 2;
	printf("PASS: %u DNS-SD public API cases; exact TXT bytes, storage growth, key rules and escaped service names.\n", cases);
	return 0;
}

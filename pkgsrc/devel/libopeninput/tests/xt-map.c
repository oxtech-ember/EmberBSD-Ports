/* SPDX-License-Identifier: BSD-2-Clause */
/*
 * Run wskbd_xt_map() of patches/patch-src_wskbdmap.c with a controlled
 * DMI: the sysctl names, the BIOS date, the order of the hwdb
 * directories, the map past the XT codes, and the selection once for
 * each process.  Usage: xt-map SCENARIO SHARE_DIR ETC_DIR
 */
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "input-event-codes.h"
#include "wskbd-hwdb.h"

struct TransMapRec {
	int begin;
	int end;
	uint32_t *map;
};

struct libinput {
	int logs;
	char message[2048];
};

static const char *share_dir, *etc_dir;
#define WSKBD_HWDB_DIR share_dir
#define WSKBD_HWDB_ETCDIR etc_dir
#define log_info(li, ...) ((li)->logs++,				\
	snprintf((li)->message, sizeof((li)->message), __VA_ARGS__))

/* The DMI strings of the system under test, by the NetBSD name. */
struct dmi_string {
	const char *name;
	const char *value;
};

static const struct dmi_string msi[] = {
	{ "bios-vendor", "American Megatrends International, LLC." },
	{ "bios-version", "E17S1IMS.10A" },
	{ "bios-date", "20250512" },
	{ "system-vendor", "Micro-Star International Co., Ltd." },
	{ "system-product", "Vector 17 HX AI A2XWJG" },
	{ "system-version", "REV:1.0" },
	{ "board-vendor", "Micro-Star International Co., Ltd." },
	{ "board-product", "MS-17S1" },
	{ "board-version", "REV:1.0" },
	{ "chassis-vendor", "Micro-Star International Co., Ltd." },
	{ "chassis-version", "N/A" },
	{ NULL, NULL },
};

static const struct dmi_string other[] = {
	{ "system-vendor", "EmberBSD Test Vendor" },
	{ "system-product", "Model 1" },
	{ NULL, NULL },
};

static const struct dmi_string dated[] = {
	{ "bios-date", "05/12/2025" },
	{ "system-vendor", "Micro-Star International Co., Ltd." },
	{ "system-product", "Vector 17 HX AI A2XWJG" },
	{ NULL, NULL },
};

static const struct dmi_string none[] = {
	{ NULL, NULL },
};

static const struct dmi_string *dmi = none;
static char requested[16][64];
static int nrequested;

static const char *
lookup(const char *name)
{
	const struct dmi_string *d;

	if (nrequested < 16)
		snprintf(requested[nrequested], sizeof(requested[0]), "%s",
		    name);
	nrequested++;
	for (d = dmi; d->name != NULL; d++)
		if (strcmp(d->name, name) == 0)
			return d->value;
	return NULL;
}

static int
copy_out(const char *value, void *buf, size_t *len)
{
	if (value == NULL) {
		errno = ENOENT;
		return -1;
	}
	if (strlen(value) + 1 > *len) {
		errno = ENOMEM;
		return -1;
	}
	*len = strlen(value) + 1;
	memcpy(buf, value, *len);
	return 0;
}

/* The test selects the sysctl path of the code, not the host. */
#ifdef OPENBSD_SYSCTL
#undef __NetBSD__
#define CTL_HW 6
#define HW_VENDOR 14
#define HW_PRODUCT 15

static int
sysctl(const int *mib, unsigned int n, void *buf, size_t *len,
    const void *nbuf, size_t nlen)
{
	const char *name;

	if (n != 2 || mib[0] != CTL_HW || nbuf != NULL || nlen != 0)
		abort();
	if (mib[1] == HW_VENDOR)
		name = "system-vendor";
	else if (mib[1] == HW_PRODUCT)
		name = "system-product";
	else
		abort();
	return copy_out(lookup(name), buf, len);
}
#else
#define __NetBSD__ 1

static int
sysctlbyname(const char *node, void *buf, size_t *len, const void *nbuf,
    size_t nlen)
{
	static const char prefix[] = "machdep.dmi.";

	if (strncmp(node, prefix, sizeof(prefix) - 1) != 0 || nbuf != NULL ||
	    nlen != 0)
		abort();
	return copy_out(lookup(node + sizeof(prefix) - 1), buf, len);
}
#endif

#include "xt-map-extract.h"

#define CHECK(e) do {							\
	if (!(e)) {							\
		fprintf(stderr, "%s: line %d: %s\n", scenario, __LINE__, #e); \
		return 1;						\
	}								\
} while (0)

static const char *scenario;

/* Codes of the map that differ from the XT map past or within it. */
static int
only(const uint32_t *map, const size_t *codes, const uint32_t *keys,
    size_t n)
{
	size_t i, j;
	uint32_t want;

	for (i = 0; i < WS_XT_HWDB_MAP_SIZE; i++) {
		want = i < WS_XT_MAP_SIZE ? wsXtMap[i] : KEY_UNKNOWN;
		for (j = 0; j < n; j++)
			if (codes[j] == i)
				want = keys[j];
		if (map[i] != want)
			return 0;
	}
	return 1;
}

int
main(int argc, char **argv)
{
	static const char *const names[] = {
		"bios-vendor", "bios-version", "bios-date", "system-vendor",
		"system-product", "system-version", "board-vendor",
		"board-product", "board-version", "chassis-vendor",
		"chassis-version",
	};
	struct libinput li = { 0, "" };
	struct TransMapRec *map, *again;
	size_t i;
	int calls;

	if (argc != 4)
		return 2;
	scenario = argv[1];
	share_dir = argv[2];
	etc_dir = argv[3];
	if (strcmp(scenario, "msi") == 0 || strcmp(scenario, "override") == 0 ||
	    strcmp(scenario, "etc-only") == 0 ||
	    strcmp(scenario, "openbsd") == 0)
		dmi = msi;
	else if (strcmp(scenario, "other") == 0)
		dmi = other;
	else if (strcmp(scenario, "dated") == 0)
		dmi = dated;
	else if (strcmp(scenario, "none") == 0)
		dmi = none;
	else
		return 2;

	map = wskbd_xt_map(&li);
	CHECK(map != NULL && map->begin == 0);
	calls = nrequested;

	/* The system does not change: the second call reads no DMI. */
	again = wskbd_xt_map(&li);
	CHECK(again == map && nrequested == calls);

	if (strcmp(scenario, "openbsd") == 0) {
		CHECK(calls == 2);
		CHECK(strcmp(requested[0], "system-vendor") == 0);
		CHECK(strcmp(requested[1], "system-product") == 0);
	} else {
		/* All the fields of the modalias, in its order. */
		CHECK(calls == 11);
		for (i = 0; i < 11; i++)
			CHECK(strcmp(requested[i], names[i]) == 0);
	}

	if (strcmp(scenario, "other") == 0 || strcmp(scenario, "none") == 0) {
		/* No records: the XT map, and no message. */
		CHECK(map == &wsXt && li.logs == 0);
		return 0;
	}

	CHECK(map == &wsXtHwdb && map->map == wsXtHwdbMap);
	CHECK(map->end == WS_XT_HWDB_MAP_SIZE && li.logs == 1);
	CHECK(strstr(li.message, " keyboard scan codes from hwdb for dmi:") !=
	    NULL);
	CHECK(strstr(li.message, ":pnVector17HXAIA2XWJG:") != NULL);
	/* The XT map entries without hwdb records stay. */
	CHECK(wsXtHwdbMap[0x76] == KEY_F24);
	for (i = 0; i < 0x80; i++)
		CHECK(wsXtHwdbMap[i] == wsXtMap[i]);

	if (strcmp(scenario, "msi") == 0) {
		/* NetBSD gives YYYYMMDD; the modalias has MM/DD/YYYY. */
		CHECK(strstr(li.message, ":bd05/12/2025:") != NULL);
		CHECK(strstr(li.message, ":rnMS-17S1:") != NULL);
		CHECK(wsXtHwdbMap[0xd7] == KEY_BLUETOOTH);
		CHECK(wsXtHwdbMap[0xf1] == KEY_F20);
		CHECK(wsXtHwdbMap[0xe4] == KEY_TOUCHPAD_TOGGLE);
	} else if (strcmp(scenario, "dated") == 0) {
		/* Another date form stays as it is. */
		CHECK(strstr(li.message, ":bd05/12/2025:") != NULL);
		CHECK(strstr(li.message, ":bvn:bvr:") != NULL);
		CHECK(wsXtHwdbMap[0xd7] == KEY_BLUETOOTH);
	} else if (strcmp(scenario, "openbsd") == 0) {
		/* Only the system vendor and product are known. */
		const char *want = "dmi:bvn:bvr:bd:"
		    "svnMicro-StarInternationalCo.,Ltd.:pnVector17HXAIA2XWJG:"
		    "pvr:rvn:rn:rvr:cvn:cvr:";

		CHECK(strstr(li.message, want) != NULL);
		CHECK(wsXtHwdbMap[0xd7] == KEY_BLUETOOTH);
		CHECK(wsXtHwdbMap[0xf1] == KEY_F20);
	} else if (strcmp(scenario, "override") == 0) {
		/* The local files come after the package files. */
		CHECK(wsXtHwdbMap[0xd7] == KEY_MUTE);
		CHECK(wsXtHwdbMap[0xf1] == KEY_F20);
		CHECK(wsXtHwdbMap[0xf0] == KEY_F13);
	} else if (strcmp(scenario, "etc-only") == 0) {
		/* Only the local records; past the XT map KEY_UNKNOWN. */
		static const size_t codes[] = { 0xd7, 0xf0 };
		static const uint32_t keys[] = { KEY_MUTE, KEY_F13 };

		CHECK(WS_XT_MAP_SIZE < 0xf0);
		CHECK(strncmp(li.message, "2 keyboard scan codes", 21) == 0);
		CHECK(only(wsXtHwdbMap, codes, keys, 2));
	}
	return 0;
}

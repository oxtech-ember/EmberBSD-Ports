/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted), public schema-option shift regression. */
#include <libxml/parser.h>
#include <libxml/xmlschemas.h>
#include <limits.h>
#include <stdio.h>

int
main(void)
{
	xmlSchemaValidCtxt *ctxt;
	const int invalid[] = { 2, INT_MIN, INT_MAX, -1 };
	size_t i;
	int result = 1;

	if (xmlSchemaSetValidOptions(NULL, 0) != -1)
		return 1;
	ctxt = xmlSchemaNewValidCtxt(NULL);
	if (ctxt == NULL)
		return 1;
	if (xmlSchemaSetValidOptions(ctxt, 0) != 0 ||
	    xmlSchemaValidCtxtGetOptions(ctxt) != 0)
		goto done;
	if (xmlSchemaSetValidOptions(ctxt, XML_SCHEMA_VAL_VC_I_CREATE) != 0 ||
	    xmlSchemaValidCtxtGetOptions(ctxt) != XML_SCHEMA_VAL_VC_I_CREATE)
		goto done;
	for (i = 0; i < sizeof(invalid) / sizeof(invalid[0]); i++) {
		if (xmlSchemaSetValidOptions(ctxt, invalid[i]) != -1 ||
		    xmlSchemaValidCtxtGetOptions(ctxt) != XML_SCHEMA_VAL_VC_I_CREATE)
			goto done;
	}
	result = 0;
done:
	xmlSchemaFreeValidCtxt(ctxt);
	xmlCleanupParser();
	if (result == 0)
		puts("Schema options preserve valid flags and reject all unsupported bits: PASS");
	return result;
}

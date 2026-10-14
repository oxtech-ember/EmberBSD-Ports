/* SPDX-License-Identifier: MIT */
#define _NETBSD_SOURCE 1
#define _GNU_SOURCE 1
#include <libxml/parser.h>
#include <libxml/tree.h>
#include <libxml/xpath.h>
#include <libxml/xmlerror.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #x); return 1; } } while (0)

static void
quiet_error(void *user, const xmlError *error)
{
	int *last_code = user;
	*last_code = error->code;
}

int
main(int argc, char **argv)
{
	const char valid[] = "<radio label='RX &amp; XML'><channel rate='1000000'>I</channel><channel rate='2000000'>Q</channel></radio>";
	const char malformed[] = "<radio><channel></radio>";
	const size_t text_size = 10 * 1024 * 1024;
	const int options = XML_PARSE_NONET | XML_PARSE_NO_XXE;
	xmlParserCtxt *ctxt;
	xmlDoc *doc, *roundtrip;
	xmlNode *root;
	xmlXPathContext *xpath;
	xmlXPathObject *result;
	xmlChar *label, *serialized;
	char *large;
	Dl_info loaded;
	void *resolved;
	int error = 0, length = 0;

	CHECK(argc == 2);
	CHECK(LIBXML_VERSION == 21504);
	CHECK(strcmp(xmlParserVersion, "21504") == 0);
	/* Resolve the definition. ELF function pointers can name the executable's PLT. */
	resolved = dlsym(RTLD_DEFAULT, "xmlReadMemory");
	CHECK(resolved != NULL && dladdr(resolved, &loaded) != 0 && loaded.dli_fname != NULL);
	CHECK(strncmp(loaded.dli_fname, argv[1], strlen(argv[1])) == 0);
	CHECK(loaded.dli_fname[strlen(argv[1])] == '/');
	printf("runtime=%s loaded=%s\n", xmlParserVersion, loaded.dli_fname);
	ctxt = xmlNewParserCtxt();
	CHECK(ctxt != NULL);
	xmlCtxtSetErrorHandler(ctxt, quiet_error, &error);
	doc = xmlCtxtReadMemory(ctxt, valid, (int)strlen(valid), "synthetic.xml", NULL, options);
	CHECK(doc != NULL && error == 0);
	root = xmlDocGetRootElement(doc);
	CHECK(root != NULL && xmlStrEqual(root->name, BAD_CAST "radio"));
	label = xmlGetProp(root, BAD_CAST "label");
	CHECK(label != NULL && xmlStrEqual(label, BAD_CAST "RX & XML"));
	xmlFree(label);
	xpath = xmlXPathNewContext(doc);
	CHECK(xpath != NULL);
	result = xmlXPathEvalExpression(BAD_CAST "sum(/radio/channel/@rate)", xpath);
	CHECK(result != NULL && result->type == XPATH_NUMBER && result->floatval == 3000000.0);
	xmlXPathFreeObject(result);
	xmlXPathFreeContext(xpath);
	xmlDocDumpMemoryEnc(doc, &serialized, &length, "UTF-8");
	CHECK(serialized != NULL && length > 0);
	roundtrip = xmlCtxtReadMemory(ctxt, (const char *)serialized, length, "roundtrip.xml", NULL, options);
	CHECK(roundtrip != NULL);
	xmlFreeDoc(roundtrip);
	xmlFree(serialized);
	xmlFreeDoc(doc);

	error = 0;
	doc = xmlCtxtReadMemory(ctxt, malformed, (int)strlen(malformed), "malformed.xml", NULL, options);
	CHECK(doc == NULL && error != 0);
	printf("malformed rejected code=%d\n", error);

	/* Exceeds the documented normal text-node limit; XML_PARSE_HUGE is absent. */
	large = malloc(text_size + 8);
	CHECK(large != NULL);
	memcpy(large, "<r>", 3);
	memset(large + 3, 'x', text_size);
	memcpy(large + 3 + text_size, "</r>", 4);
	error = 0;
	doc = xmlCtxtReadMemory(ctxt, large, (int)(text_size + 7), "oversized.xml", NULL, options);
	CHECK(doc == NULL && error == XML_ERR_RESOURCE_LIMIT);
	printf("oversized text rejected bytes=%zu code=%d\n", text_size, error);
	free(large);
	xmlFreeParserCtxt(ctxt);
	puts("PASS installed libxml2: exact provider/version, tree, attributes, XPath, serialization, malformed and oversized text rejection");
	return 0;
}

/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted), installed libclang consumer. */
#include <clang-c/Index.h>
#include <stdio.h>
#include <string.h>

static enum CXChildVisitResult
visit(CXCursor cursor, CXCursor parent, CXClientData data)
{
	unsigned *functions = data;
	(void)parent;
	if (clang_getCursorKind(cursor) == CXCursor_FunctionDecl) {
		CXString name = clang_getCursorSpelling(cursor);
		const char *text = clang_getCString(name);
		if (text != NULL && strcmp(text, "answer") == 0)
			++*functions;
		clang_disposeString(name);
	}
	return CXChildVisit_Recurse;
}

static int
parse(CXIndex index, const char *source, int invalid)
{
	const char *args[] = { "-x", "c", "-std=c11" };
	struct CXUnsavedFile file = { "ember-c-api.c", source, strlen(source) };
	CXTranslationUnit unit = NULL;
	unsigned errors = 0, functions = 0;
	int result;

	if (clang_parseTranslationUnit2(index, file.Filename, args, 3,
	    &file, 1, CXTranslationUnit_None, &unit) != CXError_Success)
		return 1;
	for (unsigned i = 0; i < clang_getNumDiagnostics(unit); ++i) {
		CXDiagnostic diagnostic = clang_getDiagnostic(unit, i);
		if (clang_getDiagnosticSeverity(diagnostic) >= CXDiagnostic_Error) {
			CXString message = clang_formatDiagnostic(diagnostic,
			    clang_defaultDiagnosticDisplayOptions());
			fprintf(stderr, "%s diagnostic: %s\n",
			    invalid ? "expected" : "unexpected", clang_getCString(message));
			clang_disposeString(message);
			++errors;
		}
		clang_disposeDiagnostic(diagnostic);
	}
	clang_visitChildren(clang_getTranslationUnitCursor(unit), visit, &functions);
	result = invalid ? errors == 0 : errors != 0 || functions != 1;
	clang_disposeTranslationUnit(unit);
	return result;
}

int
main(void)
{
	CXString version = clang_getClangVersion();
	const char *text = clang_getCString(version);
	int correct = text != NULL && strstr(text, "23.1.3") != NULL;
	CXIndex index;
	int result;

	printf("libclang: %s\n", text != NULL ? text : "missing version");
	clang_disposeString(version);
	if (!correct || (index = clang_createIndex(0, 0)) == NULL)
		return 1;
	result = parse(index, "#include <stddef.h>\nint answer(void) { return 42; }", 0);
	result |= parse(index, "int answer(void) { return ; broken syntax }", 1);
	clang_disposeIndex(index);
	if (result == 0)
		puts("PASS: installed libclang, resource header, AST and error diagnostics");
	return result;
}

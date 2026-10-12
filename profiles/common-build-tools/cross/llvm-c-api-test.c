/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted), a real shared LLVM C API consumer. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <llvm-c/Analysis.h>
#include <llvm-c/BitReader.h>
#include <llvm-c/BitWriter.h>
#include <llvm-c/Core.h>

static int
verify(LLVMModuleRef module)
{
	char *message = NULL;
	int status;

	status = LLVMVerifyModule(module, LLVMReturnStatusAction, &message);
	if (status != 0)
		fprintf(stderr, "module verification failed: %s\n", message);
	LLVMDisposeMessage(message);
	return status;
}

int
main(void)
{
	LLVMContextRef context, decoded_context;
	LLVMModuleRef module, decoded, invalid;
	LLVMTypeRef word, arguments[2], function_type;
	LLVMValueRef function, sum, result;
	LLVMBasicBlockRef block;
	LLVMBuilderRef builder;
	LLVMMemoryBufferRef bitcode;
	unsigned major, minor, patch;
	char *message = NULL;
	char *original_ir, *decoded_ir;

	LLVMGetVersion(&major, &minor, &patch);
	if (major != 23 || minor != 1 || patch != 2) {
		fprintf(stderr, "wrong runtime LLVM: %u.%u.%u\n", major,
		    minor, patch);
		return EXIT_FAILURE;
	}
	context = LLVMContextCreate();
	module = LLVMModuleCreateWithNameInContext("ember-c-api", context);
	word = LLVMInt64TypeInContext(context);
	arguments[0] = arguments[1] = word;
	function_type = LLVMFunctionType(word, arguments, 2, 0);
	function = LLVMAddFunction(module, "ember_sum", function_type);
	block = LLVMAppendBasicBlockInContext(context, function, "entry");
	builder = LLVMCreateBuilderInContext(context);
	LLVMPositionBuilderAtEnd(builder, block);
	sum = LLVMBuildAdd(builder, LLVMGetParam(function, 0),
	    LLVMGetParam(function, 1), "sum");
	result = LLVMBuildXor(builder, sum, LLVMConstInt(word, 0x5a5a, 0),
	    "result");
	LLVMBuildRet(builder, result);
	if (verify(module) != 0)
		return EXIT_FAILURE;

	/* A real malformed module must produce a verifier error. */
	invalid = LLVMModuleCreateWithNameInContext("ember-invalid", context);
	function = LLVMAddFunction(invalid, "unterminated", function_type);
	LLVMAppendBasicBlockInContext(context, function, "entry");
	if (LLVMVerifyModule(invalid, LLVMReturnStatusAction, &message) == 0 ||
	    message == NULL || strstr(message, "terminator") == NULL) {
		fprintf(stderr, "verifier did not reject the malformed module\n");
		return EXIT_FAILURE;
	}
	LLVMDisposeMessage(message);
	LLVMDisposeModule(invalid);

	bitcode = LLVMWriteBitcodeToMemoryBuffer(module);
	if (bitcode == NULL || LLVMGetBufferSize(bitcode) < 4) {
		fprintf(stderr, "empty bitcode output\n");
		return EXIT_FAILURE;
	}
	decoded_context = LLVMContextCreate();
	if (LLVMParseBitcodeInContext2(decoded_context, bitcode, &decoded) != 0 ||
	    verify(decoded) != 0)
		return EXIT_FAILURE;
	function = LLVMGetNamedFunction(decoded, "ember_sum");
	if (function == NULL || LLVMCountParams(function) != 2 ||
	    LLVMCountBasicBlocks(function) != 1) {
		fprintf(stderr, "bitcode roundtrip lost the function contract\n");
		return EXIT_FAILURE;
	}
	/* Module identifiers are container metadata, not bitcode IR content. */
	LLVMSetModuleIdentifier(decoded, "ember-c-api", strlen("ember-c-api"));
	original_ir = LLVMPrintModuleToString(module);
	decoded_ir = LLVMPrintModuleToString(decoded);
	if (strcmp(original_ir, decoded_ir) != 0) {
		fprintf(stderr, "bitcode roundtrip changed verified IR\n");
		return EXIT_FAILURE;
	}
	LLVMDisposeMessage(original_ir);
	LLVMDisposeMessage(decoded_ir);
	LLVMDisposeMemoryBuffer(bitcode);
	LLVMDisposeModule(decoded);
	LLVMContextDispose(decoded_context);
	LLVMDisposeBuilder(builder);
	LLVMDisposeModule(module);
	LLVMContextDispose(context);
	puts("PASS: LLVM 23.1.3 C API module, verifier rejection and bitcode roundtrip");
	return EXIT_SUCCESS;
}

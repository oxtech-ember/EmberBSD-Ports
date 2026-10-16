// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted), automatic NetBSD ELF JITLink acceptance.
#include <cstdint>
#include <cstring>
#include <memory>
#include <string>

#include "llvm-c/Core.h"
#include <llvm/Config/llvm-config.h>
#include "llvm/ExecutionEngine/Orc/LLJIT.h"
#include "llvm/ExecutionEngine/Orc/ObjectLinkingLayer.h"
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/Verifier.h"
#include "llvm/Support/TargetSelect.h"
#include "llvm/Support/raw_ostream.h"

using namespace llvm;
using namespace llvm::orc;

#if defined(__aarch64__)
constexpr auto expectedArch = Triple::aarch64;
#elif defined(__x86_64__)
constexpr auto expectedArch = Triple::x86_64;
#else
#error Unsupported NetBSD JIT acceptance CPU
#endif

static int failure(StringRef stage, Error error) {
  errs() << "FAIL: " << stage << ": " << toString(std::move(error)) << '\n';
  return 2;
}

static bool missing(LLJIT &jit, StringRef name) {
  auto address = jit.lookup(name);
  if (address) {
    errs() << "FAIL: missing symbol unexpectedly resolved: " << name << '\n';
    return false;
  }
  auto error = address.takeError();
  bool expected = error.isA<SymbolsNotFound>();
  auto description = toString(std::move(error));
  if (!expected) {
    errs() << "FAIL: lookup produced a different error: " << description << '\n';
    return false;
  }
  errs() << "EXPECTED-MISSING: SymbolsNotFound: " << description << '\n';
  return true;
}

static ThreadSafeModule makeModule(LLJIT &jit, unsigned cycle) {
  auto context = std::make_unique<LLVMContext>();
  auto module = std::make_unique<Module>("ember-orc", *context);
  module->setDataLayout(jit.getDataLayout());
  module->setTargetTriple(jit.getTargetTriple());
  IRBuilder<> builder(*context);
  auto *word = builder.getInt64Ty();
  auto *type = FunctionType::get(word, {word, word}, false);
  auto *function = Function::Create(type, Function::ExternalLinkage,
                                    "ember_calculate", *module);
  builder.SetInsertPoint(BasicBlock::Create(*context, "entry", function));
  auto *product = builder.CreateMul(function->getArg(0), builder.getInt64(7));
  auto *sum = builder.CreateAdd(product, function->getArg(1));
  builder.CreateRet(builder.CreateAdd(sum, builder.getInt64(cycle)));
  return ThreadSafeModule(std::move(module), std::move(context));
}

int main(int argc, char **argv) {
  bool missingOnly = argc == 2 && std::strcmp(argv[1], "--missing-symbol") == 0;
  if (argc != 1 && !missingOnly) {
    errs() << "usage: llvm-orc-test [--missing-symbol]\n";
    return 2;
  }
  unsigned major, minor, patch;
  LLVMGetVersion(&major, &minor, &patch);
  if (major != LLVM_VERSION_MAJOR || minor != LLVM_VERSION_MINOR ||
      patch != LLVM_VERSION_PATCH) {
    errs() << "FAIL: runtime LLVM version is " << major << '.' << minor << '.'
           << patch << '\n';
    return 2;
  }
  if (InitializeNativeTarget() || InitializeNativeTargetAsmPrinter() ||
      InitializeNativeTargetAsmParser()) {
    errs() << "FAIL: native target initialization\n";
    return 2;
  }
  for (unsigned cycle = 0; cycle != 4; ++cycle) {
    // No object-layer creator override: this must be upstream's automatic choice.
    auto created = LLJITBuilder().create();
    if (!created)
      return failure("LLJIT creation", created.takeError());
    auto jit = std::move(*created);
    if (jit->getTargetTriple().getArch() != expectedArch ||
        !jit->getTargetTriple().isOSNetBSD()) {
      errs() << "FAIL: runtime target differs from the compiled NetBSD CPU\n";
      return 2;
    }
    if (!isa<ObjectLinkingLayer>(jit->getObjLinkingLayer()) ||
        dynamic_cast<ObjectLinkingLayer *>(&jit->getObjLinkingLayer()) == nullptr) {
      errs() << "FAIL: automatic object layer is not JITLink with shared RTTI\n";
      return 2;
    }
    if (!missing(*jit, "ember_absent_symbol"))
      return 2;
    if (missingOnly)
      return 1; // A typed missing-symbol error must stay a failing process.

    auto tracker = jit->getMainJITDylib().createResourceTracker();
    auto module = makeModule(*jit, cycle);
    bool invalid = module.withModuleDo([](Module &m) {
      return verifyModule(m, &errs());
    });
    if (invalid)
      return 2;
    if (auto error = jit->addIRModule(tracker, std::move(module)))
      return failure("add module", std::move(error));
    auto address = jit->lookup("ember_calculate");
    if (!address)
      return failure("valid lookup after missing symbol", address.takeError());
    auto function = address->toPtr<uint64_t (*)(uint64_t, uint64_t)>();
    const uint64_t samples[][2] = {{0, 0}, {17, 29},
                                  {UINT64_C(0xfedcba9876543210), 97}};
    for (const auto &sample : samples) {
      uint64_t expected = sample[0] * 7 + sample[1] + cycle;
      if (function(sample[0], sample[1]) != expected) {
        errs() << "FAIL: generated function returned an incorrect value\n";
        return 2;
      }
    }
    if (auto error = tracker->remove())
      return failure("remove resources", std::move(error));
    if (!missing(*jit, "ember_calculate"))
      return 2;
    tracker.reset();
    jit.reset();
    outs() << "PASS: JITLink/RTTI cycle " << cycle + 1
           << " create, reject, execute, remove, dispose\n";
  }
  outs() << "PASS: LLVM 23.1.3 ORC LLJIT, four native NetBSD JITLink lifecycles\n";
  return 0;
}

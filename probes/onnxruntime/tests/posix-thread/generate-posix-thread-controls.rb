#!/usr/bin/env ruby
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Focused tests of actual ONNX Runtime source.
require 'digest'
require 'fileutils'
require 'json'
abort 'Usage: generate-posix-thread-controls.rb PRISTINE_SOURCE PATCHED_SOURCE OUTPUT' unless ARGV.length == 3
pristine, patched, output = ARGV.map { |path| File.expand_path(path) }
sources = {'baseline' => pristine, 'patched' => patched}
sources.each_value { |path| abort "Missing source directory: #{path}" unless File.directory?(path) }
FileUtils.mkdir_p(output)
FileUtils.cp(File.join(pristine, 'LICENSE'), File.join(output, 'ONNXRuntime-LICENSE'))
FileUtils.cp(File.join(pristine, 'ThirdPartyNotices.txt'), File.join(output, 'ONNXRuntime-ThirdPartyNotices'))
source_notices = "Upstream notices for the verbatim source excerpts in the generated controls.\n"
prefix = <<~'CPP'
// SPDX-License-Identifier: MIT AND Apache-2.0
// Upstream excerpts retain their notices in ONNXRuntime-SOURCE-NOTICES.
// The source block and GetErrnoInfo below are extracted from the named ORT tree.
// The harness observes real pthread APIs. It injects init/create return codes.
#include <pthread.h>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <system_error>
#include <type_traits>
#include <utility>
#if defined(__NetBSD__)
#define __real_pthread_attr_init __real___libc_thr_attr_init
#define __wrap_pthread_attr_init __wrap___libc_thr_attr_init
#define __real_pthread_attr_destroy __real___libc_thr_attr_destroy
#define __wrap_pthread_attr_destroy __wrap___libc_thr_attr_destroy
#endif
enum Fault { None, Init, Create };
static Fault fault = None;
static int initialized = 0, destroyed = 0;
extern "C" int __real_pthread_attr_init(pthread_attr_t *);
extern "C" int __real_pthread_attr_destroy(pthread_attr_t *);
extern "C" int __real_pthread_create(pthread_t *, const pthread_attr_t *, void *(*)(void *), void *);
extern "C" int __wrap_pthread_attr_init(pthread_attr_t *attr) {
  if (fault == Init) return ENOMEM;
  const int rc = __real_pthread_attr_init(attr);
  if (rc == 0) ++initialized;
  return rc;
}
extern "C" int __wrap_pthread_attr_destroy(pthread_attr_t *attr) {
  ++destroyed;
  return __real_pthread_attr_destroy(attr);
}
extern "C" int __wrap_pthread_create(pthread_t *thread, const pthread_attr_t *attr,
                                    void *(*start)(void *), void *param) {
  if (fault == Create) return EAGAIN;
  return __real_pthread_create(thread, attr, start, param);
}
template <class... T> [[noreturn]] static void Throw(T&&... values) {
  std::ostringstream text;
  (text << ... << std::forward<T>(values));
  throw std::runtime_error(text.str());
}
#define ORT_THROW(...) Throw(__VA_ARGS__)
static void *ThreadMain(void *opaque) {
  std::unique_ptr<int> param(static_cast<int *>(opaque));
  ++*param;
  return nullptr;
}
struct Options { size_t stack_size; };
CPP
suffix = <<~'CPP'
  }
  const int rc = pthread_join(hThread, nullptr);
  if (rc != 0) throw std::runtime_error("real thread join failed");
}
int main() {
  int failed = 0;
  const char *names[] = {"default", "explicit-stack", "init-failure", "stack-failure", "create-failure"};
  for (int mode = 0; mode < 5; ++mode) {
    initialized = destroyed = 0;
    fault = mode == 2 ? Init : mode == 4 ? Create : None;
    const size_t stack_size = mode == 3 ? 1 : mode == 0 ? 0 : 1024 * 1024;
    errno = ENOTTY;
    std::string message;
    bool threw = false;
    try { Exercise(Options{stack_size}); }
    catch (const std::exception& error) { threw = true; message = error.what(); }
    const int expected_code = mode == 2 ? ENOMEM : mode == 3 ? EINVAL : mode == 4 ? EAGAIN : 0;
    const char *operation = mode == 2 ? "pthread_attr_init" : mode == 3 ? "pthread_attr_setstacksize" : "pthread_create";
    const std::string expected = std::string(operation) + " failed, error code: " + std::to_string(expected_code) +
                                 " error msg: " + std::error_code(expected_code, std::generic_category()).message();
    const bool diagnostics_ok = mode < 2 ? message.empty() : message == expected;
    const bool ok = initialized == destroyed && threw == (mode >= 2) && diagnostics_ok;
    std::printf("%s %s initialized=%d destroyed=%d threw=%d diagnostics_ok=%d\n",
                ok ? "PASS" : "FAIL", names[mode], initialized, destroyed, threw, diagnostics_ok);
    if (!message.empty()) std::printf("diagnostic: %s\n", message.c_str());
    if (!ok) ++failed;
  }
  return failed == 0 ? 0 : 3;
}
CPP
receipt = {}
sources.each do |variant, source_root|
  env_path = File.join(source_root, 'onnxruntime/core/platform/posix/env.cc')
  common_path = File.join(source_root, 'onnxruntime/core/platform/env.cc')
  env = File.read(env_path)
  source_notices << "\n#{variant}: onnxruntime/core/platform/posix/env.cc\n\n" + env[0...env.index(/^#include/m)]
  first = env.index('      pthread_attr_t attr;') or abort 'Constructor attribute block is missing'
  last = env.index('      // Do not throw beyond this point', first) or abort 'Constructor block end is missing'
  block = env[first...last]
  common = File.read(common_path)
  source_notices << "\n#{variant}: onnxruntime/core/platform/env.cc\n\n" + common[0...common.index(/^#include/m)]
  get_errno = common[/std::pair<int, std::string> GetErrnoInfo\(\) \{.*?\n\}/m] or abort 'GetErrnoInfo is missing'
  declarations = "\nstatic void Exercise(const Options& thread_options) {\n  pthread_t hThread;\n  auto param_ptr = std::make_unique<int>(0);\n  {\n"
  generated = prefix + get_errno + declarations + block + suffix
  File.write(File.join(output, variant + '.cc'), generated)
  receipt[variant] = {env_path: env_path, env_sha256: Digest::SHA256.hexdigest(env), constructor_block_sha256: Digest::SHA256.hexdigest(block), first_line: env[0...first].count("\n") + 1, last_line: env[0...last].count("\n"), common_env_sha256: Digest::SHA256.hexdigest(common), errno_function_sha256: Digest::SHA256.hexdigest(get_errno), generated_sha256: Digest::SHA256.hexdigest(generated)}
end
File.write(File.join(output, 'source-contexts.json'), JSON.pretty_generate(receipt) + "\n")
File.write(File.join(output, 'ONNXRuntime-SOURCE-NOTICES'), source_notices)
licenses = %w[ONNXRuntime-LICENSE ONNXRuntime-ThirdPartyNotices ONNXRuntime-SOURCE-NOTICES].to_h do |name|
  [name, Digest::SHA256.file(File.join(output, name)).hexdigest]
end
File.write(File.join(output, 'licenses.sha256.json'), JSON.pretty_generate(licenses) + "\n")

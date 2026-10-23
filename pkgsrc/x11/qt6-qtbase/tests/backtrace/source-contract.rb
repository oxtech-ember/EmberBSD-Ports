#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
require 'json'
require 'digest'
require 'fileutils'
require 'open3'
require 'shellwords'

source, database, native_qt, output = ARGV
abort 'Usage: source-contract.rb UNPATCHED_QTBASE_SOURCE TARGET_COMPILE_COMMANDS NATIVE_QT NEW_OUTPUT' unless
  ARGV.length == 4 && ARGV.all? { |path| path.start_with?('/') }
abort 'Output already exists' if File.exist?(output) || File.symlink?(output)
original = source + '/src/corelib/global/qlogging.cpp'
abort 'Expected unpatched Qt 6.12.0 qlogging.cpp' unless Digest::SHA256.file(original).hexdigest ==
  '5533623ec288e27180c90ad394ac6849e0c66d87dcb3518d51482395948c62fd'
record = JSON.parse(File.read(database)).find { |entry| entry.fetch('file').end_with?('/qlogging.cpp') }
abort 'Actual qlogging.cpp compile command missing' unless record
arguments = record['arguments'] || Shellwords.split(record.fetch('command'))
FileUtils.mkdir_p(output)
commands = []
run = lambda do |name, command, directory = nil|
  options = {}; options[:chdir] = directory if directory
  stdout, stderr, status = Open3.capture3(*command, **options)
  File.write(output + '/' + name + '.log', stdout + stderr)
  commands << { name: name, command: command, directory: directory,
                exit_status: status.exitstatus, signal: status.termsig }
  File.write(output + '/commands.json', JSON.pretty_generate(commands) + "\n")
  [status, stdout + stderr]
end
File.write(output + '/original-compile-record.json', JSON.pretty_generate(record) + "\n")
%w[before after].each do |variant|
  directory = output + '/' + variant + '/src/corelib/global'
  FileUtils.mkdir_p(directory)
  FileUtils.copy_file(original, directory + '/qlogging.cpp', true)
end
patch = File.expand_path('../../patches/patch-src_corelib_global_qlogging.cpp', __dir__)
stdout, stderr, status = Open3.capture3('patch', '--batch', '--forward', '--fuzz=0', '-p0',
                                       '-d', output + '/after', stdin_data: File.binread(patch))
File.write(output + '/patch.log', stdout + stderr)
abort 'Canonical patch failed' unless status.success?

mini_database = []
%w[before after].each do |variant|
  file = output + '/' + variant + '/src/corelib/global/qlogging.cpp'
  command = arguments.dup
  command[command.index(record.fetch('file'))] = file
  command[command.index('-o') + 1] = output + '/' + variant + '.o'
  command += ['-iquote', File.dirname(record.fetch('file'))]
  mini_database << { directory: record.fetch('directory'), file: file, arguments: command }
  status, diagnostics = run.call(variant + '-gcc', command, record.fetch('directory'))
  if variant == 'before'
    abort 'Expected actual const-reference compilation failure' if status.success? || !diagnostics.include?('void*&') || !diagnostics.include?('const')
  else
    abort 'Patched actual translation unit failed' unless status.success?
  end
end
File.write(output + '/compile_commands.json', JSON.pretty_generate(mini_database) + "\n")

# Extract actual upstream functions. The wrapper replaces only the allocation
# API for failure injection; the parser, ownership and pointer loop stay intact.
texts = %w[before after].to_h do |variant|
  [variant, File.read(output + '/' + variant + '/src/corelib/global/qlogging.cpp')]
end
cleanup = texts.fetch('before')[/^Q_AUTOTEST_EXPORT QByteArray qCleanupFuncinfo\(QByteArray info\)\n\{.*?^\}\n/m]
abort 'Actual cleanup function missing' unless cleanup
functions = texts.transform_values do |text|
  section = text.split('#elif defined(QLOGGING_USE_EXECINFO_BACKTRACE)', 2).last
  function = section[/^static QStringList\nbacktraceFramesForLogMessage\(.*?^\}\n/m]
  abort 'Actual execinfo decoder missing' unless function
  function
end
functions['pointer-only'] = functions.delete('before').sub('void *&addr', 'void *addr')
prefix = <<~'CPP'
  #include <QtCore/private/qlogging_p.h>
  #include <QtCore/QRegularExpression>
  #include <QtCore/QStringList>
  #include <execinfo.h>
  #include <cxxabi.h>
  #include <memory>
  #include <cstdlib>
  #include <cstring>
  #include <cstdio>
  using namespace Qt::Literals;
  static const char *QtCoreLibraryName = "Qt6Core";
  static const char *mode;
  extern "C" __attribute__((noinline,visibility("default"))) void ember_qt_backtrace_symbol() {}
  static char **controlledSymbols(void *const *addresses, std::size_t count)
  {
      if (count != 1 || addresses[0] != reinterpret_cast<void *>(&ember_qt_backtrace_symbol))
          std::abort();
      if (std::strcmp(mode, "null") == 0)
          return nullptr;
      if (std::strcmp(mode, "malformed") == 0) {
          const char text[] = "invalid symbol record";
          auto storage = static_cast<char **>(std::malloc(sizeof(char *) + sizeof(text)));
          if (!storage)
              std::abort();
          storage[0] = reinterpret_cast<char *>(storage + 1);
          std::memcpy(storage[0], text, sizeof(text));
          return storage;
      }
      return ::backtrace_symbols(addresses, static_cast<int>(count));
  }
  #undef QT_FEATURE_dladdr
  #define QT_FEATURE_dladdr -1
  #define backtrace_symbols controlledSymbols
CPP
suffix = <<~'CPP'
  int main(int argc, char **argv)
  {
      if (argc != 2)
          return 2;
      mode = argv[1];
      QInternalMessageLogContext::BacktraceStorage storage;
      void *address = reinterpret_cast<void *>(&ember_qt_backtrace_symbol);
      storage.append(address);
      const auto result = backtraceFramesForLogMessage(1, storage);
      const bool preserved = storage.size() == 1 && storage[0] == address;
      const bool valid = std::strcmp(mode, "real") == 0
          ? result.size() == 1 && result[0].contains("ember_qt_backtrace_symbol"_L1)
          : result.isEmpty();
      std::printf("{\"success\":%s,\"frames\":%lld,\"pointer_preserved\":%s}\n",
                  valid && preserved ? "true" : "false", static_cast<long long>(result.size()),
                  preserved ? "true" : "false");
      return valid && preserved ? 0 : 1;
  }
CPP
cxx = ENV.fetch('CXX', 'c++')
includes = [native_qt + '/include', native_qt + '/include/QtCore', native_qt + '/include/QtCore/6.12.0', native_qt + '/include/QtCore/6.12.0/QtCore']
functions.each do |variant, function|
  cpp = output + '/focused-' + variant + '.cpp'
  binary = output + '/focused-' + variant
  File.write(cpp, prefix + cleanup + function + suffix)
  flags = ['-std=c++17', '-O1', '-g', '-fPIC', '-Wall', '-Wextra', '-Werror', '-Wl,--export-dynamic']
  flags += includes.map { |path| '-I' + path }
  status, = run.call('focused-' + variant + '-build', [cxx, *flags, cpp, '-L' + native_qt + '/lib',
                        '-Wl,-rpath,' + native_qt + '/lib', '-lQt6Core', '-pthread', '-o', binary])
  abort 'Focused real-source compile failed: ' + variant unless status.success?
  %w[real null malformed].each do |mode|
    status, diagnostics = run.call('focused-' + variant + '-' + mode,
      ['valgrind', '--tool=memcheck', '--leak-check=full', '--show-leak-kinds=all',
       '--errors-for-leak-kinds=definite,indirect', '--error-exitcode=99', binary, mode])
    if variant == 'pointer-only' && mode == 'null'
      abort 'Unguarded allocation failure was not reproduced' if status.success? ||
        !diagnostics.include?('Invalid read') || !diagnostics.include?('Address 0x0')
    else
      abort 'Focused real-source runtime failed' unless status.success?
    end
  end
end
provenance = { upstream_qlogging_sha256: Digest::SHA256.file(original).hexdigest,
               patch_sha256: Digest::SHA256.file(patch).hexdigest,
               extracted_cleanup_sha256: Digest::SHA256.hexdigest(cleanup),
               extracted_functions_sha256: functions.transform_values { |text| Digest::SHA256.hexdigest(text) },
               control: 'pointer-only applies the pointer fix without the allocation guard; final is the actual canonical patch',
               scope: 'Actual target translation-unit compile and native extracted-function Memcheck; target runtime remains separate.' }
File.write(output + '/provenance.json', JSON.pretty_generate(provenance) + "\n")
puts 'PASS: actual target compilation, native real symbol parsing, allocation failure and malformed symbol controls'

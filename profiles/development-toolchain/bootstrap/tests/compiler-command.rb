#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); real GCC16 through Autoconf-style word expansion.
require 'shellwords'
require_relative '../rebuild-libstdcxx'

abort 'Usage: compiler-command.rb TARGET NEW_PKGSRC OLD_PKGSRC GCC_ARCHIVE APP_PREFIX SYSROOT OLD_WORK NEW_WORK' unless ARGV.size == 8
args = ARGV.dup
work = File.expand_path(args.last)
builder = GCC16Runtime::LibstdcxxRebuild.new(['--check', *args])
# Run the real source/parent/compiler/SDK preflight before making test files.
builder.preflight
commands = builder.compiler_commands
FileUtils.mkdir_p(work)
results = []
run = lambda do |name, command, script, argv, want|
  out, err, status = Open3.capture3({'COMPILER' => command, 'LC_ALL' => 'C'},
    'sh', '-eu', '-c', script, 'contract', *argv)
  File.write(work + '/' + name + '.stdout', out)
  File.write(work + '/' + name + '.stderr', err)
  results << { name: name, command: command, shell: script, argv: argv,
               status: status.exitstatus }
  File.write(work + '/result.json', JSON.pretty_generate(results) + "\n")
  abort "Unexpected status for #{name}" unless status.success? == want
  [out, err]
end
source = work + '/input.c'
File.write(source, "#include <stddef.h>\nint value(void) { return (int)sizeof(ptrdiff_t); }\n")
commands.merge('GXX' => commands.fetch('CXX').sub(/-gcc /, '-g++ ')).each do |name, fixed|
  words = fixed.split(' ')
  abort 'Both GCC16 support directories must remain.' unless words.grep(/\A-B/).size == 2
  language = name == 'CC' ? 'c' : 'c++'
  baseline = Shellwords.join(words)
  before = work + '/' + name + '-before.o'
  _, err = run.call(name + '-before', baseline, '$COMPILER -x "$1" -c "$2" -o "$3"', [language, source, before], false)
  abort 'Wrong baseline failure.' unless err.include?('unrecognized command-line option') && err.include?('--sysroot\\=')
  abort 'Baseline produced an object.' if File.exist?(before)
  output = work + '/' + name + '.o'
  run.call(name + '-fixed', fixed, '$COMPILER -x "$1" -c "$2" -o "$3"', [language, source, output], true)
  elf = File.binread(output, 20)
  expected = GCC16Runtime::TARGETS.fetch(args.first).fetch(:elf_machine)
  abort 'Wrong ELF machine.' unless elf.byteslice(0, 7) == "\x7fELF\x02\x01\x01".b && elf.byteslice(18, 2).unpack1('v') == expected
  %w[crtbegin.o libgcc_s.so].each do |file|
    out, = run.call(name + '-' + file, fixed, '$COMPILER "-print-file-name=$1"', [file], true)
    abort 'Compiler selected base support.' unless File.realpath(out.strip).start_with?(File.realpath(args[5]) + '/usr/pkg/gcc16/')
  end
end
puts 'PASS: genuine CC, raw CXX and g++ reject escaped sysroot, compile target ELF and retain GCC16 support paths; no target execution.'

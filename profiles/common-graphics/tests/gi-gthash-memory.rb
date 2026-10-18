#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); causal checks of the real upstream hash test.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'

abort 'Usage: gi-gthash-memory.rb NATIVE_BUILD SOURCE_ARCHIVE GCC16_CC GCC16_AR NEW_WORK' unless ARGV.size == 5
build, archive, cc, ar = ARGV.first(4).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'New absolute output required.' unless ARGV.last.start_with?('/') && !File.exist?(work) && !File.symlink?(work)
abort 'Wrong original archive.' unless Digest::SHA256.file(archive).hexdigest == '920d1a3fcedeadc32acff95c2e203b319039dd4b4a08dd1a2dfd283d19c0b9ae'
source = File.dirname(build)
abort 'Expected a configured upstream native output directory.' unless File.basename(build) == 'output' && File.basename(source) == 'gobject-introspection-1.86.0'
patch = File.expand_path('../recipes/devel/gobject-introspection/patches/patch-girepository_gthash-memory', __dir__)
database = JSON.parse(File.read(build + '/compile_commands.json'))
log = File.dirname(source) + '/.work.log'
actual = File.readlines(log).grep(/^<\.> /).map { |line| Shellwords.split(line.delete_prefix('<.> ')) }
commands = []
FileUtils.mkdir_p(work)
run = lambda do |label, argv, cwd = work, accepted = [0]|
  stdout, stderr, status = Open3.capture3({'LC_ALL' => 'C'}, *argv, chdir: cwd, rlimit_core: 0)
  File.write(work + '/' + label + '.stdout', stdout)
  File.write(work + '/' + label + '.stderr', stderr)
  commands << {label: label, argv: argv, directory: cwd, status: status.exitstatus, signal: status.termsig}
  File.write(work + '/commands.json', JSON.pretty_generate(commands) + "\n")
  abort label + ' failed: ' + stderr unless status.exited? && accepted.include?(status.exitstatus)
  [stdout, status.exitstatus]
end
version = run.call('compiler-version', [cc, '-dumpfullversion']).first.strip
abort 'GCC 16.2.0 required.' unless version == '16.2.0'
triplet = run.call('compiler-target', [cc, '-dumpmachine']).first.strip
abort 'Native compiler required.' unless triplet.include?('linux') || triplet.include?('darwin')
run.call('archiver-version', [ar, '--version'])
valgrind = ENV.fetch('VALGRIND', 'valgrind')
run.call('memcheck-version', [valgrind, '--version'])
run.call('copy-patch', ['cp', patch, work + '/source.patch'])
inputs = [archive, cc, ar, patch, log, build + '/compile_commands.json', build + '/config.h']
compile = {}
%w[gthash.c gthash-test.c].each do |name|
  entries = database.select { |e| e.fetch('file') == '../girepository/' + name }
  abort 'Expected one real compilation entry: ' + name unless entries.size == 1
  matches = actual.select { |args| args.last(2) == ['-c', '../girepository/' + name] }
  abort 'Missing actual post-wrapper compiler invocation: ' + name if matches.empty?
  compile[name] = matches.last
  bytes = run.call('original-' + name, ['tar', '-xJOf', archive, 'gobject-introspection-1.86.0/girepository/' + name]).first
  abort 'Configured source differs from original module: ' + name unless File.binread(source + '/girepository/' + name) == bytes
  %w[baseline patched].each do |variant|
    FileUtils.mkdir_p(work + '/' + variant + '/girepository')
    File.binwrite(work + '/' + variant + '/girepository/' + name, bytes)
  end
  inputs << source + '/girepository/' + name
end
run.call('apply-patch', ['patch', '--batch', '--fuzz=0', '-p0', '-i', patch], work + '/patched')
link = actual.select { |args| args[args.index('-o').to_i + 1] == 'girepository/gthash-test' && !args.include?('-c') }.last
abort 'Missing actual upstream test link command.' unless link
inputs << build + '/girepository/cmph/libcmph.a'
# The existing CMPH archive may be thin. Preserve all of its real members too.
members = run.call('cmph-members', [ar, 't', inputs.last], build).first.lines.map(&:strip)
members.each do |name|
  path = File.expand_path(name, build)
  abort 'CMPH object escaped its configured build.' unless path.start_with?(build + '/girepository/cmph/') && File.file?(path)
  inputs << path
end
input_hashes = inputs.uniq.to_h { |p| [p, Digest::SHA256.file(p).hexdigest] }
File.write(work + '/original-commands.json', JSON.pretty_generate({cdb: database.select { |e| compile.key?(File.basename(e.fetch('file'))) }, compile: compile, link: link}) + "\n")
private_cdb = []
results = {}
%w[baseline patched].each do |variant|
  directory = work + '/' + variant
  compile.each do |name, original|
    argv = original.dup
    argv[0] = cc
    %w[-o -MF -MQ].each { |flag| argv[argv.index(flag) + 1] = directory + '/' + name + (flag == '-MF' ? '.o.d' : '.o') }
    argv[-1] = directory + '/girepository/' + name
    run.call(variant + '-' + name + '-compile', argv, build)
    private_cdb << {directory: build, arguments: argv, file: argv.last, output: directory + '/' + name + '.o'}
  end
  run.call(variant + '-archive', [ar, 'crs', directory + '/libgthash.a', directory + '/gthash.c.o'])
  argv = link.map do |arg|
    case arg
    when link.first then cc
    when 'girepository/gthash-test' then directory + '/gthash-test'
    when 'girepository/gthash-test.p/gthash-test.c.o' then directory + '/gthash-test.c.o'
    when 'girepository/libgirepository-gthash.a' then directory + '/libgthash.a'
    else arg
    end
  end
  run.call(variant + '-link', argv, build)
  output, = run.call(variant + '-test', [directory + '/gthash-test'])
  abort 'Missing upstream build/retrieve success.' unless output.include?('ok 1 /gthash/build-retrieve')
  _output, status = run.call(variant + '-memcheck', [valgrind, '--leak-check=full', '--show-leak-kinds=all', '--errors-for-leak-kinds=all', '--error-exitcode=99', '--num-callers=30', directory + '/gthash-test'], work, [0, 99])
  memory = File.read(work + '/' + variant + '-memcheck.stderr')
  counts = %w[definitely indirectly possibly].to_h do |kind|
    match = memory.match(/#{kind} lost:\s+([\d,]+) bytes in ([\d,]+) blocks/)
    abort 'Missing Memcheck summary.' unless match
    [kind, match.captures.map { |v| v.delete(',').to_i }]
  end
  reachable = memory.match(/still reachable:\s+([\d,]+) bytes in ([\d,]+) blocks/)
  abort 'Missing reachable summary.' unless reachable
  invalid = memory.lines.grep(/Invalid (?:read|write|free)|uninitialised|uninitialized|Mismatched free|overlap|Fishy/)
  abort 'Unexpected invalid-access or uninitialized-value diagnostic.' unless invalid.empty?
  abort 'Unexpected suppressed allocations.' unless memory.match?(/suppressed:\s+0 bytes in 0 blocks/)
  contexts = memory.scan(/bytes in [\d,]+ blocks are (?:definitely lost|indirectly lost|possibly lost|still reachable) in loss record/).size
  errors = memory.match(/ERROR SUMMARY: ([\d,]+) errors from ([\d,]+) contexts \(suppressed: 0 from 0\)/)
  abort 'Unexpected non-leak error contexts.' unless errors && errors.captures.map { |v| v.delete(',').to_i } == [contexts, contexts]
  abort 'Strict all-leak exit status changed.' unless status == (contexts.zero? ? 0 : 99)
  expected = variant == 'baseline' ? {'definitely' => [80, 2], 'indirectly' => [55, 4], 'possibly' => [0, 0]} : {'definitely' => [0, 0], 'indirectly' => [0, 0], 'possibly' => [0, 0]}
  abort 'Unexpected causal leak totals.' unless counts == expected
  results[variant] = {status: status, error_contexts: contexts, lost: counts, reachable: reachable.captures.map { |v| v.delete(',').to_i }, executable_sha256: Digest::SHA256.file(directory + '/gthash-test').hexdigest}
end
abort 'Inherited reachable allocations changed.' unless results['baseline'][:reachable] == results['patched'][:reachable]
abort 'Input changed while checking.' unless input_hashes.all? { |p, hash| Digest::SHA256.file(p).hexdigest == hash }
File.write(work + '/compile_commands.json', JSON.pretty_generate(private_cdb) + "\n")
File.write(work + '/result.json', JSON.pretty_generate({
  scope: 'Two real upstream C modules with actual native pkgsrc compiler/link flags and unchanged CMPH; no package or target acceptance. Strict all-leak Memcheck retains inherited reachable contexts without suppressions.',
  compiler: version, compiler_target: triplet, inputs: input_hashes, results: results
}) + "\n")
puts 'PASS: two owned leaks removed; inspect the preserved strict Memcheck status and inherited reachable findings.'

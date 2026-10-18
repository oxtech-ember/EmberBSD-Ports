#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real ELF fixtures; rejected inputs never reach SSH.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'rbconfig'
require 'shellwords'
# A native launcher can supply a private Ruby runtime without target LD paths.
ruby = ENV.fetch('EMBERBSD_TEST_RUBY', RbConfig.ruby)
abort 'EMBERBSD_TEST_RUBY must name an absolute executable' unless ruby.start_with?('/') && File.file?(ruby) && File.executable?(ruby)
ruby = File.realpath(ruby)
target = 'aarch64'
if ARGV.first == '--target'
  ARGV.shift; target = ARGV.shift
end
targets = {'aarch64' => ['aarch64', 'aarch64--netbsd', 183], 'amd64' => ['x86_64', 'x86_64--netbsd', 62]}
abort 'Usage: gi-query-contract.rb [--target aarch64|amd64] CROSS_TOOLS NEW_WORK' unless ARGV.size == 2 && targets.key?(target)
processor, triplet, machine = targets.fetch(target)
cc = File.realpath(ARGV[0] + '/bin/' + triplet + '-gcc')
readelf = File.realpath(ARGV[0] + '/bin/' + triplet + '-readelf')
work = File.expand_path(ARGV[1])
abort 'new absolute work required' unless ARGV[1].start_with?('/') && !File.exist?(work)
FileUtils.mkdir_p(work)
work = File.realpath(work)
%w[build build/provider sysroot cache bin outside].each { |d| FileUtils.mkdir_p(work + '/' + d) }
helper = File.expand_path('../recipes/devel/gobject-introspection/files/target-query.rb', __dir__)
needed = File.expand_path('../recipes/devel/gobject-introspection/files/elf-needed.sh', __dir__)
run = lambda do |name, *command, **options|
  output, status = Open3.capture2e(*command, **options)
  File.write(work + '/' + name + '.log', output)
  abort "#{name}: #{output}" unless status.success?
  output
end
run.call('native-ruby-version', ruby, '--version')
File.write(work + '/native-ruby-provider.json', JSON.pretty_generate({path: ruby, sha256: Digest::SHA256.file(ruby).hexdigest}) + "\n")
File.write(work + '/build/library.c', 'int gi_probe_answer(void) { return 42; }' + "\n")
File.write(work + '/build/query.c', 'extern int gi_probe_answer(void); void _start(void) { (void)gi_probe_answer(); }' + "\n")
run.call('dso', cc, '-nostdlib', '-shared', '-fPIC', work + '/build/library.c', '-Wl,-soname,libgi-probe.so.1', '-o', work + '/build/provider/libgi-probe.so.1')
run.call('elf', cc, '-nostdlib', '-Wl,-e,_start', work + '/build/query.c', '-L' + work + '/build/provider', '-Wl,-l:libgi-probe.so.1', '-o', work + '/build/query')
File.symlink(work + '/build/provider', work + '/provider-alias')
marker = work + '/ssh-reached'
File.write(work + '/bin/ssh', "#!/bin/sh\nprintf '%s\\n' \"$@\" > #{(work + '/ssh-arguments').shellescape}\nprintf '%s\\n' reached >> #{marker.shellescape}\nexit 74\n")
File.chmod(0755, work + '/bin/ssh')
config = {'build_root' => work + '/build', 'sysroot' => work + '/sysroot',
          'cache' => work + '/cache', 'readelf' => readelf, 'ssh' => 'unused.invalid',
          'library_dirs' => [work + '/provider-alias']}
config['target'] = target if target != 'aarch64'
config_path = work + '/config.json'
File.write(config_path, JSON.pretty_generate(config))
env = {'EMBERBSD_GI_QUERY_CONFIG' => config_path, 'PATH' => work + '/bin:/usr/bin:/bin',
       'LD_LIBRARY_PATH' => nil, 'DYLD_LIBRARY_PATH' => nil, 'LD_PRELOAD' => nil}
reject = lambda do |name, pattern, *args|
  output, status = Open3.capture2e(env, ruby, helper, *args)
  File.write(work + '/' + name + '.log', output)
  abort "#{name} did not fail at expected boundary: #{output}" if status.success? || !output.match?(pattern) || File.exist?(marker)
end
run.call('check', env, ruby, helper, '--check', work + '/build', work + '/sysroot', readelf, target)
# Real bmake evaluates the shared GI fragment for both target metadata sets.
# This is a variable-selection fixture; it does not accept providers or a VM.
make_tree = work + '/make'
FileUtils.mkdir_p([make_tree + '/devel/gobject-introspection', make_tree + '/mk'])
File.write(make_tree + '/mk/bsd.prefs.mk', '')
FileUtils.cp(File.expand_path('../cross.mk', File.dirname(helper)), make_tree + '/devel/gobject-introspection/cross.mk')
File.write(make_tree + '/devel/gobject-introspection/Makefile', ".include \"cross.mk\"\n")
make_base = [ENV.fetch('BMAKE', 'bmake'), '-C', make_tree + '/devel/gobject-introspection',
  'USE_CROSS_COMPILE=yes', 'OPSYS=NetBSD', 'CROSS_OPSYS=NetBSD', 'CROSS_OS_VERSION=11.0',
  'EMBERBSD_GI_RUBY=' + ruby, 'EMBERBSD_GI_QUERY_CONFIG=' + config_path,
  'EMBERBSD_CROSS_BUILD_CC=/usr/bin/cc', 'TOOLDIR=' + ARGV[0]]
targets.to_a.reverse_each do |selected, (arch, gnu, _)|
  args = ['MACHINE_ARCH=' + arch, 'CROSS_MACHINE_ARCH=' + arch, 'MACHINE_GNU_PLATFORM=' + gnu, 'EMBERBSD_CROSS_TARGET=' + selected]
  fail_reason = run.call('make-' + selected, *make_base, *args, '-V', '${PKG_FAIL_REASON}')
  abort 'supported GI target rejected: ' + fail_reason unless fail_reason.strip.empty?
  settings = run.call('make-env-' + selected, *make_base, *args, '-V', '${MAKE_ENV}')
  abort 'GI selected a foreign target readelf/environment' unless settings.include?('/bin/' + gnu + '-readelf') && settings.include?('EMBERBSD_GI_TARGET=' + selected)
  foreign = arch == 'aarch64' ? 'x86_64' : 'aarch64'
  rejected = run.call('make-mixed-' + selected, *make_base, *args, 'CROSS_MACHINE_ARCH=' + foreign, '-V', '${PKG_FAIL_REASON}')
  abort 'GI accepted mixed architecture metadata' if rejected.strip.empty?
  rejected = run.call('make-mixed-gnu-' + selected, *make_base, *args, 'MACHINE_GNU_PLATFORM=foreign--netbsd', '-V', '${PKG_FAIL_REASON}')
  abort 'GI accepted a foreign GNU provider' if rejected.strip.empty?
end
File.write(config_path, JSON.pretty_generate(config.merge('host_key_alias' => 'unsafe alias')))
reject.call('invalid-host-alias', /invalid host key alias/, '--check', work + '/build', work + '/sysroot', readelf)
config['host_key_alias'] = 'target.example'
File.write(config_path, JSON.pretty_generate(config))
reject.call('different-sysroot', /configuration differs/, '--check', work + '/build', work + '/outside', readelf)
reject.call('outside-binary', /outside build root/, '/usr/bin/true')
FileUtils.cp('/usr/bin/true', work + '/build/native')
reject.call('native-binary', /not little-endian .* ELF64/, work + '/build/native')
other_target = target == 'aarch64' ? 'amd64' : 'aarch64'
File.write(config_path, JSON.pretty_generate(config.merge('target' => other_target)))
reject.call('foreign-query-config', /configuration differs|not little-endian .* ELF64/, '--check', work + '/build', work + '/sysroot', readelf, target)
reject.call('foreign-query-architecture', /not little-endian .* ELF64/, work + '/build/query')
legacy = config.dup; legacy.delete('target')
File.write(config_path, JSON.pretty_generate(legacy))
if target == 'amd64'
  reject.call('legacy-is-not-amd64', /configuration differs/, '--check', work + '/build', work + '/sysroot', readelf, target)
end
run.call('legacy-aarch64-check', env, ruby, helper, '--check', work + '/build', work + '/sysroot', readelf)
File.write(config_path, JSON.pretty_generate(config.merge('target' => 'unsupported')))
reject.call('unknown-target', /unsupported GI target/, '--check', work + '/build', work + '/sysroot', readelf)
File.write(config_path, JSON.pretty_generate(config))
provider = work + '/build/provider/libgi-probe.so.1'
bytes = File.binread(provider)
foreign = bytes.dup; foreign[18, 2] = [machine == 62 ? 183 : 62].pack('v')
File.binwrite(provider, foreign)
reject.call('foreign-provider', /not little-endian .* ELF64/, work + '/build/query')
foreign = bytes.dup; foreign.setbyte(4, 1)
File.binwrite(provider, foreign)
reject.call('foreign-class', /not little-endian .* ELF64/, work + '/build/query')
foreign = bytes.dup; foreign.setbyte(5, 2)
File.binwrite(provider, foreign)
reject.call('foreign-endian', /not little-endian .* ELF64/, work + '/build/query')
File.binwrite(provider, bytes)
reject.call('unsupported-args', /only an optional/, work + '/build/query', '--delete')
File.write(work + '/build/types', 'get-type:gi_probe_answer' + "\n")
File.write(work + '/outside/untouched', 'unchanged')
File.symlink(work + '/outside/untouched', work + '/build/output')
reject.call('output-symlink', /output already exists/, work + '/build/query', '--introspect-dump=' + work + '/build/types,' + work + '/build/output')
abort 'symlink target modified' unless File.read(work + '/outside/untouched') == 'unchanged'
File.write(config_path, JSON.pretty_generate(config.merge('library_dirs' => [])))
reject.call('missing-provider', /missing provider: libgi-probe.so.1/, work + '/build/query')
File.write(config_path, JSON.pretty_generate(config.merge('sysroot' => work + '/build')))
reject.call('overlapping-roots', /build\/sysroot overlap/, '--check', work + '/build', work + '/build', readelf)
File.write(config_path, JSON.pretty_generate(config))
# This real cross-linked fixture can resolve only through the symlinked directory.
# The deliberately refusing SSH executable proves resolution reached that boundary.
output, status = Open3.capture2e(env, ruby, helper, work + '/build/query')
File.write(work + '/valid-alias.log', output)
abort 'valid target/alias did not reach bounded transport' unless !status.success? && output.include?('allocate failed (74)') && File.read(marker) == "reached\n"
allocation = File.readlines(work + '/ssh-arguments', chomp: true).last
abort 'selected target uname contract missing' unless allocation.include?('test "$(uname -s)" = NetBSD') && allocation.include?('test "$(uname -p)" = ' + processor)
# Literal execute arguments are valid. They still use the same verified transport.
File.unlink(marker)
output, status = Open3.capture2e(env, ruby, helper, '--execute', work + '/build/query', 'two words', "single'quote", '')
File.write(work + '/execute-args.log', output)
abort 'execute argv did not reach bounded transport' unless !status.success? && output.include?('allocate failed (74)') && File.read(marker) == "reached\n"
# Execute only the production identity shell body, with explicit host fixtures.
# No VM, SSH target or target executable is run by this regression.
identity_glue = <<~SH
  uname() { case "$1" in -s) printf '%s\\n' "$GI_FIXTURE_OPSYS";; -p) printf '%s\\n' "$GI_FIXTURE_PROCESSOR";; *) return 2;; esac; }
  mktemp() { printf 'allocated\\n' > #{(work + '/identity-allocated').shellescape}; printf '/tmp/ember-gir.AbCd1234\\n'; }
SH
[['NetBSD', processor, true], ['NetBSD', processor == 'aarch64' ? 'x86_64' : 'aarch64', false], ['Linux', processor, false]].each do |os, arch, accepted|
  FileUtils.rm_f(work + '/identity-allocated')
  output, status = Open3.capture2e({'GI_FIXTURE_OPSYS' => os, 'GI_FIXTURE_PROCESSOR' => arch}, 'sh', '-s', stdin_data: identity_glue + allocation)
  abort 'remote identity did not gate allocation' unless status.success? == accepted && File.exist?(work + '/identity-allocated') == accepted
end
puts 'PASS: both target make metadata sets, explicit/default JSON targets, foreign ELF/class/endian and real identity shell guard'
out = run.call('needed', {'EMBERBSD_GI_READELF' => readelf, 'EMBERBSD_GI_TARGET' => target}, 'sh', needed, work + '/build/query')
abort 'wrong target SONAME' unless out == "libgi-probe.so.1\n"
_, status = Open3.capture2e({'EMBERBSD_GI_READELF' => readelf, 'EMBERBSD_GI_TARGET' => target}, 'sh', needed, work + '/build/native')
abort 'native image accepted by SONAME helper' if status.success?
_, status = Open3.capture2e({'EMBERBSD_GI_READELF' => readelf, 'EMBERBSD_GI_TARGET' => other_target}, 'sh', needed, work + '/build/query')
abort 'foreign machine accepted by SONAME helper' if status.success?
['', 'unsupported'].each do |invalid|
  output, status = Open3.capture2e({'EMBERBSD_GI_READELF' => readelf, 'EMBERBSD_GI_TARGET' => invalid}, 'sh', needed, work + '/build/query')
  abort 'empty or unknown SONAME target did not fail closed' if status.success? || !output.include?('unsupported GI target')
end
# Inject transport outcomes only; this does not emulate target execution.
# Separate board acceptance runs actual cross-built upstream test binaries.
File.write(work + '/bin/ssh', "#!#{ruby}\n" + <<~'RUBY')
  command = ARGV.last
  mode = ENV.fetch('GI_TEST_MODE')
  phase = case command
          when /mktemp/ then 'allocate'
          when /\Atar / then 'transfer'
          when 'sh -s -- ember-gir-reuse' then 'reuse'
          when 'sh -s' then 'query'
          when /\Acat .*execution.status/ then 'status'
          when /\Atest -s / then 'readback'
          when /\Arm -rf / then 'cleanup'
          else abort 'unexpected test transport command'
          end
  File.open(ENV.fetch('GI_TEST_PHASES'), 'a') { |f| f.puts(phase) }
  STDIN.read if %w[transfer query reuse].include?(phase)
  exit 74 if mode == phase
  case phase
  when 'allocate' then puts '/tmp/ember-gir.AbCd1234'
  when 'reuse'
    puts 'unexpected.so' if mode == 'reuse-unknown'
    puts ['libgi-probe.so.1', 'libgi-probe.so.1'] if mode == 'reuse-duplicate'
    puts 'libgi-probe.so.1' if mode == 'reused'
  when 'query'
    if mode.start_with?('execute-')
      STDOUT.write("probe stdout\n")
      STDERR.write("probe stderr\n")
      exit(mode == 'execute-fail' ? 7 : 0)
    end
    File.write(ENV.fetch('GI_TEST_INPUT'), 'modified') if mode == 'input-change'
  when 'status'
    puts(mode == 'execute-fail' ? '7' : '0')
  when 'readback'
    puts(mode == 'bad-xml' ? 'not XML' : '<dump></dump>')
  end
RUBY
File.unlink(work + '/build/output')
# Subsequent transport fixtures select a real sysroot ELF provider. The earlier
# alias test keeps exercising an in-tree provider that must always be uploaded.
FileUtils.mkdir_p(work + '/sysroot/usr/pkg/lib')
FileUtils.cp(work + '/build/provider/libgi-probe.so.1', work + '/sysroot/usr/pkg/lib')
File.write(config_path, JSON.pretty_generate(config.merge('library_dirs' => [work + '/sysroot/usr/pkg/lib'])))
expected = {
  'reuse' => ['allocate reuse cleanup', /reuse failed/],
  'reuse-unknown' => ['allocate reuse cleanup', /invalid reused library response/],
  'reuse-duplicate' => ['allocate reuse cleanup', /invalid reused library response/],
  'reused' => ['allocate reuse transfer query readback cleanup', nil],
  'transfer' => ['allocate reuse transfer cleanup', /transfer failed/],
  'query' => ['allocate reuse transfer query cleanup', /target query failed/],
  'readback' => ['allocate reuse transfer query readback cleanup', /invalid introspection XML/],
  'bad-xml' => ['allocate reuse transfer query readback cleanup', /invalid introspection XML/],
  'cleanup' => ['allocate reuse transfer query readback cleanup', /remote cleanup failed/],
  'input-change' => ['allocate reuse transfer query readback cleanup', /source providers changed/],
  'success' => ['allocate reuse transfer query readback cleanup', nil]
}
expected.each do |mode, (phases, error)|
  File.write(work + '/build/types', "original type query\n")
  trace = work + '/' + mode + '-phases.txt'
  outcome = work + '/build/' + mode + '.xml'
  transport_env = env.merge('GI_TEST_MODE' => mode, 'GI_TEST_PHASES' => trace,
                            'GI_TEST_INPUT' => work + '/build/types')
  output, status = Open3.capture2e(transport_env, ruby, helper,
                                 work + '/build/query',
                                 "--introspect-dump=#{work}/build/types,#{outcome}")
  File.write(work + '/transport-' + mode + '.log', output)
  abort "#{mode}: wrong transport phases" unless File.read(trace).split == phases.split
  if error
    abort "#{mode}: wrong failure boundary: #{output}" if status.success? || !output.match?(error)
    abort "#{mode}: published failed output" if File.exist?(outcome)
  else
    abort "#{mode}: valid output missing: #{output}" unless status.success? && File.read(outcome) == "<dump></dump>\n"
  end
end
# Execute the production reuse shell body, not a rewritten copy algorithm.
# Only the fixture's target paths and sha256 command are mapped to this host.
reuse_body = File.read(Dir.glob(work + '/cache/*/reuse.sh').first)
reuse_root = work + '/reuse-shell'
installed = work + '/sysroot/usr/pkg/lib/libgi-probe.so.1'
body = reuse_body.gsub('/tmp/ember-gir.AbCd1234', reuse_root).gsub('/usr/pkg/lib/libgi-probe.so.1', installed)
sha_glue = "sha256() { test \"$1\" = -q || return 2; shift; /usr/bin/shasum -a 256 \"$1\" | cut -d ' ' -f 1; }\n"
%w[matched changed missing corrupted-copy].each do |mode|
  FileUtils.rm_rf(reuse_root)
  FileUtils.mkdir_p(reuse_root)
  FileUtils.cp(work + '/build/provider/libgi-probe.so.1', installed)
  File.write(installed, 'different installed file') if mode == 'changed'
  File.unlink(installed) if mode == 'missing'
  corruption = mode == 'corrupted-copy' ? "cp() { /bin/cp \"$1\" \"$2\" && printf corrupted >> \"$2\"; }\n" : ''
  output, status = Open3.capture2e('sh', '-s', stdin_data: sha_glue + corruption + body)
  File.write(work + '/reuse-shell-' + mode + '.log', output)
  copied = reuse_root + '/lib/libgi-probe.so.1'
  case mode
  when 'matched'
    abort 'reuse did not copy matching provider' unless status.success? && output == "libgi-probe.so.1\n" &&
      Digest::SHA256.file(copied) == Digest::SHA256.file(installed)
  when 'changed', 'missing'
    abort 'reuse did not fall back to transfer' unless status.success? && output.empty? && !File.exist?(copied)
  else
    abort 'reuse accepted corrupt copied bytes' unless status.exitstatus == 92 && output.empty?
  end
end
puts 'PASS: production reuse shell copies identical bytes, falls back for missing/changed files and rejects copy corruption'
puts 'PASS: real ELF and alias resolution; seven refusals before SSH; SONAME checks; nine transport failures, installed-provider reuse and successful publication'
# General configure probes preserve stdout, stderr and a legitimate failure code.
%w[execute-pass execute-fail].each do |mode|
  phase_file = work + '/' + mode + '-phases'
  stdout, stderr, status = Open3.capture3(env.merge('GI_TEST_MODE' => mode,
    'GI_TEST_PHASES' => phase_file), ruby, helper, '--execute', work + '/build/query')
  expected_status = mode == 'execute-fail' ? 7 : 0
  abort "#{mode}: lost probe streams/status" unless stdout == "probe stdout\n" &&
    stderr == "probe stderr\n" && status.exitstatus == expected_status
  abort "#{mode}: missing cleanup" unless File.readlines(phase_file, chomp: true) ==
    %w[allocate reuse transfer query status cleanup]
end
puts 'PASS: execute mode preserves separate streams and negative exit status, cleans both outcomes and accepts literal arguments'
%w[query status cleanup].each do |mode|
  failure_marker = work + '/build/' + mode + '-failure'
  output, status = Open3.capture2e(env.merge('GI_TEST_MODE' => mode,
    'GI_TEST_PHASES' => work + '/execute-' + mode + '-phases',
    'EMBERBSD_GI_FAILURE_MARKER' => failure_marker), ruby, helper,
    '--execute', work + '/build/query')
  abort "Unrecorded execute infrastructure failure: #{mode}: #{output}" if status.success? || !File.file?(failure_marker)
end
puts 'PASS: query/status/cleanup failures cannot become silent negative configure results'

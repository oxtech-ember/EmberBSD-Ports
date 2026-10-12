#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real ELF fixtures; rejected inputs never reach SSH.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'rbconfig'
require 'shellwords'
abort 'Usage: gi-query-contract.rb CROSS_TOOLS NEW_WORK' unless ARGV.size == 2
cc = File.realpath(ARGV[0] + '/bin/aarch64--netbsd-gcc')
readelf = File.realpath(ARGV[0] + '/bin/aarch64--netbsd-readelf')
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
File.write(work + '/build/library.c', 'int gi_probe_answer(void) { return 42; }' + "\n")
File.write(work + '/build/query.c', 'extern int gi_probe_answer(void); void _start(void) { (void)gi_probe_answer(); }' + "\n")
run.call('dso', cc, '-nostdlib', '-shared', '-fPIC', work + '/build/library.c', '-Wl,-soname,libgi-probe.so.1', '-o', work + '/build/provider/libgi-probe.so.1')
run.call('elf', cc, '-nostdlib', '-Wl,-e,_start', work + '/build/query.c', '-L' + work + '/build/provider', '-Wl,-l:libgi-probe.so.1', '-o', work + '/build/query')
File.symlink(work + '/build/provider', work + '/provider-alias')
marker = work + '/ssh-reached'
File.write(work + '/bin/ssh', "#!/bin/sh\nprintf '%s\\n' reached >> #{marker.shellescape}\nexit 74\n")
File.chmod(0755, work + '/bin/ssh')
config = {'build_root' => work + '/build', 'sysroot' => work + '/sysroot',
          'cache' => work + '/cache', 'readelf' => readelf, 'ssh' => 'unused.invalid',
          'library_dirs' => [work + '/provider-alias']}
config_path = work + '/config.json'
File.write(config_path, JSON.pretty_generate(config))
env = {'EMBERBSD_GI_QUERY_CONFIG' => config_path, 'PATH' => work + '/bin:/usr/bin:/bin',
       'LD_LIBRARY_PATH' => nil, 'DYLD_LIBRARY_PATH' => nil, 'LD_PRELOAD' => nil}
reject = lambda do |name, pattern, *args|
  output, status = Open3.capture2e(env, RbConfig.ruby, helper, *args)
  File.write(work + '/' + name + '.log', output)
  abort "#{name} did not fail at expected boundary: #{output}" if status.success? || !output.match?(pattern) || File.exist?(marker)
end
run.call('check', env, RbConfig.ruby, helper, '--check', work + '/build', work + '/sysroot', readelf)
File.write(config_path, JSON.pretty_generate(config.merge('host_key_alias' => 'unsafe alias')))
reject.call('invalid-host-alias', /invalid host key alias/, '--check', work + '/build', work + '/sysroot', readelf)
config['host_key_alias'] = 'target.example'
File.write(config_path, JSON.pretty_generate(config))
reject.call('different-sysroot', /configuration differs/, '--check', work + '/build', work + '/outside', readelf)
reject.call('outside-binary', /outside build root/, '/usr/bin/true')
FileUtils.cp('/usr/bin/true', work + '/build/native')
reject.call('native-binary', /not little-endian AArch64 ELF64/, work + '/build/native')
reject.call('unsupported-args', /only an optional/, work + '/build/query', '--delete')
reject.call('execute-args', /only an optional/, '--execute', work + '/build/query', '--delete')
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
output, status = Open3.capture2e(env, RbConfig.ruby, helper, work + '/build/query')
File.write(work + '/valid-alias.log', output)
abort 'valid target/alias did not reach bounded transport' unless !status.success? && output.include?('allocate failed (74)') && File.read(marker) == "reached\n"
out = run.call('needed', {'EMBERBSD_GI_READELF' => readelf}, 'sh', needed, work + '/build/query')
abort 'wrong target SONAME' unless out == "libgi-probe.so.1\n"
_, status = Open3.capture2e({'EMBERBSD_GI_READELF' => readelf}, 'sh', needed, work + '/build/native')
abort 'native image accepted by SONAME helper' if status.success?
# Inject transport outcomes only; this does not emulate target execution.
# Separate board acceptance runs actual cross-built upstream test binaries.
File.write(work + '/bin/ssh', "#!#{RbConfig.ruby}\n" + <<~'RUBY')
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
  output, status = Open3.capture2e(transport_env, RbConfig.ruby, helper,
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
    'GI_TEST_PHASES' => phase_file), RbConfig.ruby, helper, '--execute', work + '/build/query')
  expected_status = mode == 'execute-fail' ? 7 : 0
  abort "#{mode}: lost probe streams/status" unless stdout == "probe stdout\n" &&
    stderr == "probe stderr\n" && status.exitstatus == expected_status
  abort "#{mode}: missing cleanup" unless File.readlines(phase_file, chomp: true) ==
    %w[allocate reuse transfer query status cleanup]
end
puts 'PASS: execute mode preserves separate streams and negative exit status, cleans both outcomes and rejects arguments'
%w[query status cleanup].each do |mode|
  failure_marker = work + '/build/' + mode + '-failure'
  output, status = Open3.capture2e(env.merge('GI_TEST_MODE' => mode,
    'GI_TEST_PHASES' => work + '/execute-' + mode + '-phases',
    'EMBERBSD_GI_FAILURE_MARKER' => failure_marker), RbConfig.ruby, helper,
    '--execute', work + '/build/query')
  abort "Unrecorded execute infrastructure failure: #{mode}: #{output}" if status.success? || !File.file?(failure_marker)
end
puts 'PASS: query/status/cleanup failures cannot become silent negative configure results'

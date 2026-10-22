#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Run GI queries against real EmberBSD target libraries.
require 'json'
require 'open3'
require 'fileutils'
require 'digest'
require 'shellwords'
require 'tmpdir'

config = JSON.parse(File.read(ENV.fetch('EMBERBSD_GI_QUERY_CONFIG')))
target = config.fetch('target', 'aarch64')
targets = {'aarch64' => ['aarch64', 'AArch64'], 'amd64' => ['x86_64', 'Advanced Micro Devices X86-64']}
abort 'unsupported GI target' unless targets.key?(target)
processor, machine = targets.fetch(target)
abort 'configuration differs from recipe target' if ENV.key?('EMBERBSD_GI_TARGET') && ENV.fetch('EMBERBSD_GI_TARGET') != target
absolute = lambda do |key|
  value = config.fetch(key)
  abort "#{key} must be absolute" unless value.is_a?(String) && value.start_with?('/')
  File.realpath(value)
end
base = absolute.call('build_root')
sysroot = absolute.call('sysroot')
cache = absolute.call('cache')
readelf = absolute.call('readelf')
abort 'readelf is not executable' unless File.executable?(readelf)
roots = [base, sysroot]
inside = lambda { |path, root| path == root || path.start_with?(root + '/') }
abort 'build/sysroot overlap' if inside.call(base, sysroot) || inside.call(sysroot, base)
abort 'cache overlaps providers' if inside.call(cache, sysroot) || inside.call(sysroot, cache)
host = config.fetch('ssh')
abort 'invalid SSH destination' unless host.is_a?(String) && host.match?(/\A(?:[A-Za-z0-9_][A-Za-z0-9_.-]*@)?[A-Za-z0-9][A-Za-z0-9_.-]*\z/)
ssh = ['ssh', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
       '-o', 'ConnectTimeout=5', '-o', 'ServerAliveInterval=10',
       '-o', 'ServerAliveCountMax=3']
if config.key?('host_key_alias')
  key_alias = config.fetch('host_key_alias')
  abort 'invalid host key alias' unless key_alias.is_a?(String) && key_alias.match?(/\A[A-Za-z0-9][A-Za-z0-9_.-]*\z/)
  ssh += ['-o', "HostKeyAlias=#{key_alias}"]
end
ssh << host
if ARGV.first == '--check'
  abort 'usage: --check WORKDIR SYSROOT READELF [aarch64|amd64]' unless [4, 5].include?(ARGV.size)
  expected_target = ARGV[4] || 'aarch64'
  workdir, target_root, tool = ARGV[1, 3].map { |p| File.realpath(p) }
  abort 'configuration differs from recipe' unless inside.call(workdir, base) && target_root == sysroot && tool == readelf && expected_target == target
  puts 'PASS: GI query configuration matches the selected work, sysroot and readelf'
  exit
end

execute = ARGV.first == '--execute'
ARGV.shift if execute
query_complete = false
if execute && ENV.key?('EMBERBSD_GI_FAILURE_MARKER')
  failure_marker = ENV.fetch('EMBERBSD_GI_FAILURE_MARKER')
  abort 'failure marker outside build root' unless failure_marker.start_with?('/') &&
    inside.call(File.realpath(File.dirname(failure_marker)), base) && !File.symlink?(failure_marker)
  at_exit do
    unless query_complete
      begin
        File.open(failure_marker, File::WRONLY | File::CREAT | File::EXCL, 0600) do |f|
          f.puts 'Target query did not complete with verified execution and cleanup.'
        end
      rescue Errno::EEXIST
        # Keep the first failed query visible to the enclosing configure step.
      end
    end
  end
end
name = ARGV.shift || abort('binary required')
# Waf's CHECK_COMMAND runs selected base utilities on the target, for example
# `getconf LFS_CFLAGS`. Execute mode runs the sysroot's own program with its
# sysroot providers. It never runs a program from the target's PATH.
target_commands = {'getconf' => '/usr/bin/getconf'}
if !name.include?('/')
  abort "unsupported target command: #{name}" unless execute && target_commands.key?(name)
  command = sysroot + target_commands.fetch(name)
  abort "target command missing from sysroot: #{name}" unless File.file?(command)
  exe = File.realpath(command)
  abort 'target command outside sysroot' unless inside.call(exe, sysroot)
else
  exe = File.realpath(name)
  abort 'binary outside build root' unless inside.call(exe, base)
end
args = ARGV.dup
abort 'only an optional introspect-dump argument is supported' unless execute || args.empty? || (args.size == 1 && args.first.start_with?('--introspect-dump='))
in_path = out_path = nil
if !execute && args.any?
  in_path, out_path = args.first.delete_prefix('--introspect-dump=').split(',', 2)
  abort 'invalid dump paths' unless in_path && out_path && in_path.start_with?('/') && out_path.start_with?('/')
  in_path = File.realpath(in_path)
  abort 'dump paths outside build root' unless inside.call(in_path, base) && inside.call(File.realpath(File.dirname(out_path)), base)
  abort 'dump output already exists' if File.exist?(out_path) || File.symlink?(out_path)
end
work = Dir.mktmpdir('gi-query-', cache)
stage = work + '/stage'
FileUtils.mkdir_p(stage + '/lib')
run = lambda do |name, *command, **opts|
  out, status = Open3.capture2e(*command, **opts)
  File.write(work + '/' + name + '.log', out)
  abort "#{name} failed (#{status.exitstatus}); see #{work}" unless status.success?
  out
end
# Resolve aliases before sysroot mapping. A host /usr/lib is never a provider.
mapdir = lambda do |path|
  if File.directory?(path)
    resolved = File.realpath(path)
    next resolved if roots.any? { |root| inside.call(resolved, root) }
  end
  if roots.any? { |root| inside.call(path, root) }
    path
  elsif path.start_with?('/')
    sysroot + path
  else
    File.expand_path(path, Dir.pwd)
  end
end
# Extra directories may select in-tree target libraries. They do not establish
# sysroot provenance; conflicting selected providers fail.
search = config.fetch('library_dirs', []) + ENV.fetch('LD_LIBRARY_PATH', '').split(':')
search = search.reject(&:empty?).map { |p| mapdir.call(p) }.uniq
defaults = %w[/usr/pkg/gcc16/lib /usr/pkg/lib /usr/lib /lib].map { |p| mapdir.call(p) }
files = {}
pending = [exe]
until pending.empty?
  file = pending.shift
  header, status = Open3.capture2e(readelf, '-h', file)
  actual_machine = header[/^\s*Machine:\s*(.*?)\s*$/, 1]
  abort "not little-endian #{processor} ELF64: #{file}" unless status.success? && actual_machine == machine && header.match?(/Class:.*ELF64/) && header.match?(/Data:.*little endian/)
  dyn, status = Open3.capture2e(readelf, '-d', file)
  abort 'readelf failed' unless status.success?
  localdirs = dyn.scan(/\((?:RPATH|RUNPATH)\).*\[(.*?)\]/).flatten.flat_map { |s| s.split(':') }.map do |p|
    mapdir.call(p.gsub('${ORIGIN}', File.dirname(file)).gsub('$ORIGIN', File.dirname(file)))
  end
  dyn.scan(/\(NEEDED\).*\[(.*?)\]/).flatten.each do |name|
    abort 'unsafe SONAME' unless name.match?(/\A[a-zA-Z0-9._+-]+\z/)
    candidate = (search + localdirs + defaults).map { |d| d + '/' + name }.find { |p| File.file?(p) }
    abort "missing provider: #{name}" unless candidate
    candidate = File.realpath(candidate)
    abort 'provider outside target/build roots' unless roots.any? { |r| inside.call(candidate, r) }
    if files[name]
      abort "conflicting #{name}: #{files[name]} versus #{candidate}" unless Digest::SHA256.file(candidate).hexdigest == Digest::SHA256.file(files[name]).hexdigest
    else
      files[name] = candidate
      pending << candidate
    end
  end
end
sources = ([exe] + files.values + [in_path].compact).uniq.sort.to_h { |p| [p, Digest::SHA256.file(p).hexdigest] }
FileUtils.cp(exe, stage + '/query')
File.chmod(0755, stage + '/query')
files.each { |name, path| FileUtils.cp(path, stage + '/lib/' + name) }
FileUtils.cp(in_path, stage + '/types.txt') if in_path
entries = Dir.glob(stage + '/**/*').select { |p| File.file?(p) }.sort
manifest = entries.map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p.delete_prefix(stage + '/')}\n" }.join
File.write(stage + '/files.sha256', manifest)
File.write(work + '/files.sha256', manifest)
File.write(work + '/sources.sha256', sources.map { |p, h| "#{h}  #{p}\n" }.join)
remote = nil
begin
  remote = run.call('allocate', *ssh, 'test "$(uname -s)" = NetBSD && test "$(uname -p)" = ' + processor + ' && umask 077 && mktemp -d /tmp/ember-gir.XXXXXXXX').strip
  abort 'invalid temporary directory' unless remote.match?(/\A\/tmp\/ember-gir\.[A-Za-z0-9]{8}\z/)
# Reuse only byte-identical installed sysroot providers, copied into this
# query's private directory. In-tree libraries always travel with the query.
# Both normal manifest checks below still cover every reused byte.
reusable = files.select { |_name, path| inside.call(path, sysroot) }
unless reusable.empty?
  reuse_script = "set -eu\ncd #{remote.shellescape}\nmkdir -p lib\n"
  reusable.each do |name, path|
    installed = path.delete_prefix(sysroot)
    expected = sources.fetch(path)
    copy = 'lib/' + name
    reuse_script += <<~SH
      if test -f #{installed.shellescape} && test "$(sha256 -q #{installed.shellescape})" = #{expected}; then
        cp #{installed.shellescape} #{copy.shellescape}
        test "$(sha256 -q #{copy.shellescape})" = #{expected} || exit 92
        printf '%s\n' #{name.shellescape}
      fi
    SH
  end
  File.write(work + '/reuse.sh', reuse_script)
  reused = run.call('reuse', *ssh, 'sh -s -- ember-gir-reuse', stdin_data: reuse_script).lines.map(&:chomp)
  abort 'invalid reused library response' unless reused.uniq == reused && reused.all? { |name| reusable.key?(name) }
  reused.each { |name| File.unlink(stage + '/lib/' + name) }
end
run.call('tar', '/usr/bin/env', 'COPYFILE_DISABLE=1', 'tar', '--format=ustar', '--no-xattrs', '-czf', work + '/input.tar.gz', '-C', stage, '.')
File.write(work + '/transfer-size.txt', "#{File.size(work + '/input.tar.gz')}\n")

  run.call('transfer', *ssh, "tar -xzf - -C #{remote.shellescape}", stdin_data: File.binread(work + '/input.tar.gz'))
  invocation = [remote + '/query']
  invocation.concat(args) if execute
  invocation << "--introspect-dump=#{remote}/types.txt,#{remote}/dump.xml" if out_path
  script = <<~SH
    set -eu
    cd #{remote.shellescape}
    while read hash name; do
      test "$(sha256 -q "$name")" = "$hash" || exit 90
    done < files.sha256
    ulimit -c 0
    ulimit -f 16384
    export LD_LIBRARY_PATH=#{(remote + '/lib').shellescape}
    unset LD_PRELOAD
    set +e
    timeout -k 5 60 #{invocation.shelljoin} > stdout.log 2> stderr.log
    result=$?
    set -e
    while read hash name; do
      test "$(sha256 -q "$name")" = "$hash" || exit 91
    done < files.sha256
    cat stdout.log
    cat stderr.log >&2
    printf '%s\n' "$result" > execution.status
    exit "$result"
  SH
  if execute
    output, diagnostics, status = Open3.capture3(*ssh, 'sh -s', stdin_data: script)
    File.write(work + '/target.log', output)
    File.write(work + '/target-stderr.log', diagnostics)
    # Configure probes need their actual stdout and exit status, including a
    # legitimate negative result. Do not merge diagnostics into feature data.
    $stdout.write(output)
    $stderr.write(diagnostics)
  else
    output, status = Open3.capture2e(*ssh, 'sh -s', stdin_data: script)
    File.write(work + '/target.log', output)
    $stderr.write(output)
  end
  target_status = status.exitstatus || 1
  File.write(work + '/exit.txt', "#{target_status}\n")
  if execute
    receipt = run.call('execution-status', *ssh, "cat #{remote}/execution.status").strip
    abort 'target execution receipt differs from transport status' unless receipt == target_status.to_s
  end
  abort "target query failed (#{target_status}), #{work}" unless execute || status.success?
  if out_path
    xml, diagnostics, status = Open3.capture3(*ssh, "test -s #{remote}/dump.xml && cat #{remote}/dump.xml")
    File.write(work + '/xml-transfer.log', "exit=#{status.exitstatus} bytes=#{xml.bytesize}\n" + diagnostics)
    File.binwrite(work + '/dump.xml', xml) if xml.bytesize <= 16 * 1024 * 1024
    abort 'invalid introspection XML' unless status.success? && xml.bytesize <= 16 * 1024 * 1024 && xml.include?('<dump')
  end
ensure
  if remote && remote.match?(/\A\/tmp\/ember-gir\.[A-Za-z0-9]{8}\z/)
    out, status = Open3.capture2e(*ssh, "rm -rf -- #{remote.shellescape}")
    File.write(work + '/cleanup.log', "#{status.exitstatus}\n" + out)
    abort "remote cleanup failed: #{remote}" unless status.success?
  end
end
abort 'source providers changed during query' unless sources.all? { |p, h| Digest::SHA256.file(p).hexdigest == h }
File.open(out_path, File::WRONLY | File::CREAT | File::EXCL, 0600) { |out| out.write(xml) } if out_path
FileUtils.rm_rf(stage)
File.unlink(work + '/input.tar.gz')
query_complete = true
exit target_status if execute

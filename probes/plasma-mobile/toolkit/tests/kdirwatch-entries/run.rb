#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
# Build complete KDirWatch and verify entry lifecycle with real native Qt.
require 'digest'
require 'fileutils'
require 'json'
require 'optparse'
require 'timeout'

options = { jobs: 2, cmake: ENV.fetch('PATH').split(File::PATH_SEPARATOR)
  .map { |dir| File.join(dir, 'cmake') }.find { |path| File.executable?(path) } }
parser = OptionParser.new do |p|
  p.banner = 'Usage: run.rb ARCHIVE NEW_OUTPUT QT_PREFIX --ecm-dir ECM_DIR [options]'
  p.on('--ecm-dir PATH') { |v| options[:ecm] = v }
  p.on('--jobs COUNT', Integer) { |v| options[:jobs] = v }
  p.on('--cmake PATH') { |v| options[:cmake] = v }
end
parser.parse!
abort parser.to_s unless ARGV.length == 3 && options[:ecm]
abort 'CMake and a positive job count are required' unless options[:cmake] && options[:jobs] > 0
archive = File.realpath(ARGV[0])
output = File.expand_path(ARGV[1])
qt = File.realpath(ARGV[2])
ecm = File.realpath(options[:ecm])
abort 'Output must be a new directory' if File.exist?(output) || File.symlink?(output)
recipe = File.expand_path('../../recipes/devel/kf6-kcoreaddons', __dir__)
distinfo = File.read(recipe + '/distinfo')
expected = distinfo[/^SHA512 \(kcoreaddons-6.31.0.tar.xz\) = (\h+)$/, 1]
abort 'Archive checksum mismatch' unless expected && Digest::SHA512.file(archive).hexdigest == expected
baseline_patch = __dir__ + '/nb3.patch'
abort 'Retained nb3 patch checksum mismatch' unless Digest::SHA256.file(baseline_patch).hexdigest ==
  '3a5252072d757cd8fafc67c9badc685d8b2c4cbe01c3536dcdbe16b63887c5de'
patches = Dir[recipe + '/patches/patch-*'].sort
patches.each do |patch|
  expected = distinfo[/^SHA1 \(#{Regexp.escape(File.basename(patch))}\) = (\h+)$/, 1]
  canonical = File.readlines(patch).reject { |line| line.match?(/\$NetBSD.*/) }.join
  abort 'Recipe patch checksum mismatch: ' + patch unless expected && Digest::SHA1.hexdigest(canonical) == expected
end
FileUtils.mkdir_p(output + '/tmp')
environment = { 'TMPDIR' => output + '/tmp',
  'ASAN_OPTIONS' => 'halt_on_error=1:abort_on_error=1',
  'UBSAN_OPTIONS' => 'halt_on_error=1:print_stacktrace=1' }
commands = []
run = lambda do |label, argv, cwd: nil, fatal: nil, timeout: 600|
  argv = argv.map(&:to_s)
  stdout = output + '/' + label + '.stdout'
  stderr = output + '/' + label + '.stderr'
  spawn_options = { in: File::NULL, out: stdout, err: stderr, pgroup: true, rlimit_core: 0 }
  spawn_options[:chdir] = cwd if cwd
  pid = Process.spawn(environment, *argv, **spawn_options)
  timed_out = false
  begin
    _, status = Timeout.timeout(timeout) { Process.wait2(pid) }
  rescue Timeout::Error
    timed_out = true
    Process.kill('TERM', -pid)
    begin
      _, status = Timeout.timeout(2) { Process.wait2(pid) }
    rescue Timeout::Error
      Process.kill('KILL', -pid)
      _, status = Process.wait2(pid)
    end
  end
  commands << { label: label, argv: argv, cwd: cwd,
    returncode: status.signaled? ? -status.termsig : status.exitstatus, timed_out: timed_out }
  File.write(output + '/commands.json', JSON.pretty_generate(commands) + "\n")
  raise label + ' timed out' if timed_out
  if fatal
    unless status.signaled? && status.termsig == Signal.list.fetch('ABRT') &&
        File.read(stderr).include?('CHECK failed: ' + fatal)
      raise label + ' did not reach the expected fatal CHECK'
    end
  else
    raise label + ' failed; read its stderr' unless status.success?
  end
end

source_parent = output + '/source'
FileUtils.mkdir_p(source_parent)
run.call('extract', ['tar', '-xf', archive, '-C', source_parent])
source = source_parent + '/kcoreaddons-6.31.0'
implementation = source + '/src/lib/io/kdirwatch.cpp'
original = File.binread(implementation)
patches.each do |patch|
  run.call('apply-' + File.basename(patch), ['patch', '-p0', '-F', '0', '-i', patch], cwd: source)
end
candidate = File.read(implementation)
File.binwrite(implementation, original)
run.call('apply-nb3', ['patch', '-p0', '-F', '0', '-i', baseline_patch], cwd: source)
baseline = File.read(implementation)
abort 'Retained nb3 source changed' unless Digest::SHA256.hexdigest(baseline) ==
  '8a369c1d30fa3a480c920f968ba1e340c404e55b749582d5eba4e3fb7426fc14'
old_loop = <<~'CPP'.lines.map { |line| '            ' + line }.join.chomp
  for (Entry *sub_entry : std::as_const(entry->m_entries)) {
      fswEventReceived(sub_entry->path); // recurse, to call scanEntry and see if something changed
  }
CPP
new_loop = <<~'CPP'.lines.map { |line| '            ' + line }.join.chomp
  // Scanning a child can remove it from this list and delete the parent entry.
  QStringList subEntryPaths;
  subEntryPaths.reserve(entry->m_entries.size());
  for (const Entry *sub_entry : std::as_const(entry->m_entries)) {
      subEntryPaths.append(sub_entry->path);
  }
  for (const QString &subEntryPath : std::as_const(subEntryPaths)) {
      fswEventReceived(subEntryPath); // look up each child again after earlier scans
  }
CPP
guard = "        } else if (entry->m_status == Normal) {\n            /* Even though QFileSystemWatcher"
abort 'Source regression anchors changed' unless candidate.scan(new_loop).length == 1 &&
  candidate.scan(guard).length == 1 && baseline.scan(old_loop).length == 1
variants = { 'baseline' => baseline, 'candidate' => candidate,
  'live-children' => candidate.sub(new_loop, old_loop),
  'missing-reregister' => candidate.sub(guard, "        } else {\n            /* Even though QFileSystemWatcher") }
variants.each { |name, text| File.write(output + '/' + name + '-kdirwatch.cpp', text) }
metadata = {
  archive: { path: archive, sha256: Digest::SHA256.file(archive).hexdigest },
  patches: patches.to_h { |p| [File.basename(p), Digest::SHA256.file(p).hexdigest] },
  test_sources: Dir[__dir__ + '/*'].select { |p| File.file?(p) }
    .to_h { |p| [File.basename(p), Digest::SHA256.file(p).hexdigest] },
  variants: variants.transform_values { |text| Digest::SHA256.hexdigest(text) },
  scope: 'Complete upstream library and Qt containers/filesystem services. Only KDirWatch NetBSD backend policy is selected on the native host. No target kqueue or package claim.' }
File.write(output + '/source.json', JSON.pretty_generate(metadata) + "\n")
build = output + '/normal'
run.call('configure', [options[:cmake], '-S', __dir__, '-B', build, '-G', 'Ninja',
  '-DCMAKE_BUILD_TYPE=Debug', '-DCMAKE_PREFIX_PATH=' + qt, '-DECM_DIR=' + ecm, '-DUPSTREAM_SOURCE=' + source])
modes = %w[children missing parent-removal]
expected = { 'children' => 'child->m_status == KDirWatchPrivate::Normal',
  'parent-removal' => 'child->m_status == KDirWatchPrivate::Normal',
  'missing' => 'entry(state, parent).m_entries.size() == 1' }
cases = { 'baseline' => modes, 'candidate' => modes,
  'live-children' => %w[children parent-removal], 'missing-reregister' => %w[missing] }
begin
  variants.each do |name, text|
    File.write(implementation, text)
    run.call('build-' + name, [options[:cmake], '--build', build, '--target', 'kdirwatch-entry-contract',
      '--parallel', options[:jobs]])
    cases.fetch(name).each do |mode|
      run.call(name + '-' + mode, [build + '/kdirwatch-entry-contract', mode],
        fatal: name == 'candidate' ? nil : expected.fetch(mode), timeout: 30)
    end
  end
ensure
  File.write(implementation, candidate)
end
sanitized = output + '/sanitized'
run.call('configure-sanitized', [options[:cmake], '-S', __dir__, '-B', sanitized, '-G', 'Ninja',
  '-DCMAKE_BUILD_TYPE=Debug', '-DCMAKE_PREFIX_PATH=' + qt, '-DECM_DIR=' + ecm,
  '-DUPSTREAM_SOURCE=' + source, '-DCONTRACT_SANITIZE=ON'])
run.call('build-sanitized', [options[:cmake], '--build', sanitized, '--target', 'kdirwatch-entry-contract',
  '--parallel', options[:jobs]])
modes.each { |mode| run.call('sanitized-' + mode, [sanitized + '/kdirwatch-entry-contract', mode], timeout: 30) }
run.call('build-final-candidate', [options[:cmake], '--build', build, '--target', 'kdirwatch-entry-contract',
  '--parallel', options[:jobs]])
result = { baseline: 'three intended fatal CHECK failures', candidate: 'three scenarios PASS',
  controls: 'live children traversal and missing-file re-registration compiled and reached their expected CHECK',
  asan_ubsan: 'three candidate scenarios PASS', scope: metadata[:scope] }
File.write(output + '/results.json', JSON.pretty_generate(result) + "\n")
puts 'PASS: complete KDirWatch entry lifecycle, causal baseline/controls, ASan/UBSan'

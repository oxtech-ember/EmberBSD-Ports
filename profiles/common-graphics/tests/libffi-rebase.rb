#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Reproduce and check the libffi 3.8 source rebase.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'

abort 'Usage: libffi-rebase.rb DISTFILES NEW_WORK [PINNED_PKGSRC]' unless (2..3).cover?(ARGV.size)
profile = File.expand_path('..', __dir__)
ports = File.expand_path('../..', profile)
archives, work = ARGV.take(2).map { |path| File.expand_path(path) }
pkgsrc = File.expand_path(ARGV[2] || ports + '/upstream/pkgsrc')
recipe = profile + '/../../pkgsrc/devel/libffi'
original_recipe = pkgsrc + '/devel/libffi'
archive = archives + '/libffi-3.8.0.tar.gz'
pin = File.readlines(profile + '/sources.tsv').map { |line| line.split("\t") }.find { |fields| fields.first == 'devel/libffi' }
abort 'Missing source pin' unless pin
abort 'Archive SHA256 mismatch' unless Digest::SHA256.file(archive).hexdigest == pin.fetch(2)
info = File.read(recipe + '/distinfo')
sha512 = info[/^SHA512 \(libffi-3\.8\.0\.tar\.gz\) = ([0-9a-f]{128})$/, 1]
abort 'Archive SHA512 mismatch' unless sha512 && Digest::SHA512.file(archive).hexdigest == sha512
abort 'Use a new work directory' if File.exist?(work)
FileUtils.mkdir_p(work)

def command(argv, log, expect_success: true, input: nil)
  options = {}
  options[:stdin_data] = File.binread(input) if input
  out, status = Open3.capture2e(*argv, **options)
  File.binwrite(log, out)
  abort "Unexpected status #{status.exitstatus}: #{log}" unless status.success? == expect_success
  out
end

baseline = work + '/baseline'
fixed = work + '/fixed'
[baseline, fixed].each do |source|
  FileUtils.mkdir_p(source)
  command(['tar', '-xf', archive, '--strip-components=1', '-C', source], source + '-extract.log')
end
original = original_recipe + '/patches/patch-src_powerpc_ffi__powerpc.h'
abort 'Missing pinned original patch' unless File.file?(original)
filtered = File.binread(original).lines.reject { |line| line.match?(/[$]NetBSD.*/) }.join
abort 'Unexpected baseline patch' unless Digest::SHA1.hexdigest(filtered) == 'fafb125b28069d5108726ac7b2d4efdc4fdadf92'
# Patch implementations format diagnostics differently. Compare the rejected
# hunk, including its line counts and full context. Offsets may differ.
def hunks(text)
  text.lines.slice_before { |line| line.start_with?('@@ ') }.map do |lines|
    next unless lines.first.start_with?('@@ ')
    match = lines.first.match(/^@@ -\d+,(\d+) \+\d+,(\d+) @@/)
    return nil unless match
    [match[1], match[2], lines.drop(1).join]
  end.compact
end

original_hunks = hunks(File.binread(original))
abort 'Expected three original hunks' unless original_hunks.size == 3
expected_reject = [original_hunks.last]
command(['patch', '-f', '-N', '-F', '0', '-p0', '-d', baseline], work + '/baseline-failure.log', expect_success: false, input: original)
reject = baseline + '/src/powerpc/ffi_powerpc.h.rej'
abort 'Baseline did not write rejects' unless File.file?(reject)
rejected = File.binread(reject)
abort 'Baseline did not reject exactly the third hunk' unless hunks(rejected) == expected_reject
# Reject unrelated failures, multiple failed hunks, and changed context/counts.
controls = ['', "@@ -1,6 +1,7 @@\n" + original_hunks.first[2],
  rejected + rejected, rejected.sub('float128', 'wrong_type'),
  rejected.sub(/(@@ -\d+),9/, '\\1,8'), rejected.sub('@@ -', '@@ invalid -')]
abort 'Reject comparison accepts another failure' if controls.any? { |value| hunks(value) == expected_reject }

patches = info.scan(/^SHA1 \((patch-[^)]+)\) = ([0-9a-f]{40})$/).sort
abort 'Expected all thirteen original patch paths' unless patches.size == 13
patches.each do |name, hash|
  path = recipe + '/patches/' + name
  filtered = File.binread(path).lines.reject { |line| line.match?(/[$]NetBSD.*/) }.join
  abort 'Patch checksum mismatch: ' + name unless Digest::SHA1.hexdigest(filtered) == hash
  command(['patch', '-f', '-N', '-F', '0', '-p0', '-d', fixed], work + '/' + name + '.log', input: path)
end
out, status = Open3.capture2('tar', '-xOf', archive, 'libffi-3.8.0/src/powerpc/ffi_powerpc.h')
abort 'Cannot read original header' unless status.success?
expected = out.sub('#if defined(__FLOAT128_TYPE__) && defined(__HAVE_FLOAT128)', "#ifdef POWERPC64\n#if defined(__FLOAT128_TYPE__) && defined(__HAVE_FLOAT128)")
expected = expected.sub("typedef char float128[16] __attribute__((aligned(16)));\n#endif", "typedef char float128[16] __attribute__((aligned(16)));\n#endif\n#endif /* POWERPC64 */")
abort 'Baseline did not apply only the first two hunks' unless File.binread(baseline + '/src/powerpc/ffi_powerpc.h') == expected.b
expected = expected.sub('int FFI_HIDDEN ffi_closure_helper_LINUX64 (ffi_cif *,', "#ifdef POWERPC64\nint FFI_HIDDEN ffi_closure_helper_LINUX64 (ffi_cif *,")
expected = expected.sub("\t\t\t\t\t   float128 *);", "\t\t\t\t\t   float128 *);\n#endif")
actual = File.binread(fixed + '/src/powerpc/ffi_powerpc.h')
abort 'Rebase changed more than the two original ILP32 guards' unless expected.b == actual
command(['patch', '-f', '-N', '-F', '0', '-p0', '-d', fixed], work + '/repeated-patch.log', expect_success: false, input: recipe + '/patches/patch-src_powerpc_ffi__powerpc.h')
File.write(work + '/result.json', JSON.pretty_generate({'archive_sha256' => Digest::SHA256.file(archive).hexdigest,
  'canonical_patches' => patches.size, 'baseline_third_hunk_failed' => true, 'two_original_guards_only' => true,
  'unrelated_reject_controls' => controls.size, 'fixed_header_sha256' => Digest::SHA256.hexdigest(actual), 'powerpc_runtime_tested' => false}) + "\n")
puts 'PASS: stale hunk fails; all thirteen canonical patches apply without fuzz; both original ILP32 guards and repeat rejection are preserved'

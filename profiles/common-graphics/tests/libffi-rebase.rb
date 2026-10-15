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
recipe = profile + '/recipes/devel/libffi'
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
failure = command(['patch', '-f', '-N', '-F', '0', '-p0', '-d', baseline], work + '/baseline-failure.log', expect_success: false, input: original)
abort 'Baseline did not reproduce the third-hunk failure' unless failure.include?('Hunk #3 FAILED') && File.file?(baseline + '/src/powerpc/ffi_powerpc.h.rej')

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
expected = expected.sub('int FFI_HIDDEN ffi_closure_helper_LINUX64 (ffi_cif *,', "#ifdef POWERPC64\nint FFI_HIDDEN ffi_closure_helper_LINUX64 (ffi_cif *,")
expected = expected.sub("\t\t\t\t\t   float128 *);", "\t\t\t\t\t   float128 *);\n#endif")
actual = File.binread(fixed + '/src/powerpc/ffi_powerpc.h')
abort 'Rebase changed more than the two original ILP32 guards' unless expected.b == actual
command(['patch', '-f', '-N', '-F', '0', '-p0', '-d', fixed], work + '/repeated-patch.log', expect_success: false, input: recipe + '/patches/patch-src_powerpc_ffi__powerpc.h')
File.write(work + '/result.json', JSON.pretty_generate({'archive_sha256' => Digest::SHA256.file(archive).hexdigest,
  'canonical_patches' => patches.size, 'baseline_third_hunk_failed' => true, 'two_original_guards_only' => true,
  'fixed_header_sha256' => Digest::SHA256.hexdigest(actual), 'powerpc_runtime_tested' => false}) + "\n")
puts 'PASS: stale hunk fails; all thirteen canonical patches apply without fuzz; both original ILP32 guards and repeat rejection are preserved'

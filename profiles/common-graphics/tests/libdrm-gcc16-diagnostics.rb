#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Replay real target compiler inputs privately.
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'
abort 'usage: libdrm-gcc16-diagnostics.rb PKGSRC MAKECONF CONFIGURED_SOURCE NEW_OUTPUT' unless ARGV.length == 4
tree, config, original = ARGV.first(3).map { |path| File.realpath(path) }
work = File.expand_path(ARGV.last)
abort 'new absolute output required' unless ARGV.last.start_with?('/') && !File.exist?(work)
Dir.mkdir(work)
profile = File.expand_path('..', __dir__)
recipe = profile + '/../../pkgsrc/x11/libdrm'
FileUtils.mkdir_p(work + '/pkgsrc/x11')
Dir.children(tree).each { |p| File.symlink(tree + '/' + p, work + '/pkgsrc/' + p) unless p == 'x11' }
Dir.children(tree + '/x11').each { |p| File.symlink(tree + '/x11/' + p, work + '/pkgsrc/x11/' + p) unless p == 'libdrm' }
FileUtils.cp_r(recipe, work + '/pkgsrc/x11/libdrm')
# Use this checkout's matching profile beside the real exported owner markers.
profile_copy = work + '/pkgsrc/EMBERBSD-COMMON-GRAPHICS-MK.CONF'
File.unlink(profile_copy)
FileUtils.cp(profile + '/mk.conf', profile_copy)
text = File.read(config).gsub(/"[^"]+\/EMBERBSD-COMMON-GRAPHICS-MK.CONF"/, '"' + profile_copy + '"')
File.write(work + '/mk.conf', text)
config = work + '/mk.conf'
command = [ENV.fetch('BMAKE', 'bmake'), '-C', work + '/pkgsrc/x11/libdrm',
  'MAKECONF=' + config, 'WRKOBJDIR=' + work + '/objects',
  '-V', '${CFLAGS}', '-V', '${PKG_FAIL_REASON}', '-V', '${MACHINE_ARCH}']
output, status = Open3.capture2e(*command)
File.write(work + '/metadata.log', output)
abort 'real pkgsrc metadata query failed: ' + output unless status.success?
cflags, failures, arch = output.lines.map(&:strip)
abort 'prepared amd64 cross metadata required: ' + output unless failures.empty? && arch == 'x86_64'
flags = Shellwords.split(cflags)
errors = []
errors << 'recipe warning flags lost during MAKECONF parsing' unless %w[-Werror -Wno-error=cpp].all? { |f| flags.include?(f) }
source = work + '/source'
FileUtils.cp_r(original, source)
patch = recipe + '/patches/patch-include_drm_i915__drm.h'
if File.file?(patch)
  output, status = Open3.capture2e('/usr/bin/patch', '-f', '-p0', '-F0', '-i', patch, chdir: source)
  File.write(work + '/patch.log', output)
  abort 'new source patch did not apply cleanly: ' + output unless status.success?
end
# Use the already recorded post-wrapper compiler invocation. Do not invoke a
# wrapper that logs into the active work tree. All source and output paths move.
log = File.read(File.dirname(original) + '/.work.log')
units = %w[intel/intel_bufmgr.c intel/intel_bufmgr_fake.c intel/intel_bufmgr_gem.c xf86drm.c]
units.each do |unit|
  matches = log.lines.select { |l| l.start_with?('<.> ') && l.include?(' -c ../' + unit + ' ') }
  abort 'one actual post-wrapper invocation required: ' + unit unless matches.length == 1
  line = matches.fetch(0)
  args = Shellwords.split(line.delete_prefix('<.> ').strip).map { |arg| arg.gsub(original, source) }
  args += flags.reject { |flag| args.include?(flag) }
  FileUtils.mkdir_p(File.dirname(source + '/output/' + args.fetch(args.index('-o') + 1)))
  File.write(work + '/' + File.basename(unit) + '.command.json', JSON.pretty_generate(args))
  out, status = Open3.capture2e(*args, chdir: source + '/output')
  File.write(work + '/' + File.basename(unit) + '.log', out)
  errors << unit + ' did not compile: ' + out unless status.success?
end
abort errors.map { |e| 'FAIL: ' + e }.join("\n") unless errors.empty?
# Assert the four unchanged layouts with the same target compiler. Their
# packing diagnostic remains visible. A new, unrelated packed record fails.
compiler = JSON.parse(File.read(work + '/intel_bufmgr.c.command.json')).first
sysroot = JSON.parse(File.read(work + '/intel_bufmgr.c.command.json')).find { |a| a.start_with?('--sysroot=') }
abi = profile + '/tests/libdrm-i915-abi.c'
base = [compiler, sysroot, '-std=c11', '-Wall', '-Werror', '-Wpacked', '-I' + source + '/include/drm'].compact
out, status = Open3.capture2e(*base, '-c', abi, '-o', work + '/abi.o')
File.write(work + '/abi.log', out)
abort 'target uAPI layout mismatch: ' + out unless status.success? && out.scan(/warning: packed attribute is unnecessary/).length == 4
negative = work + '/negative.c'
File.write(negative, "#include <i915_drm.h>\nstruct unrelated { unsigned int value; } __attribute__((packed));\n")
out, status = Open3.capture2e(*base, '-c', negative, '-o', work + '/negative.o')
File.write(work + '/negative.log', out)
abort 'unrelated packed diagnostic lost Werror' if status.success? || !out.include?("'unrelated'") || !out.include?('-Werror=packed')
# Host execution checks only the header's unaligned field-access boundary.
# It does not execute the target object or establish a DRM device result.
native = ENV.fetch('HOST_CC', '/usr/bin/clang')
out, status = Open3.capture2e(native, '-std=c11', '-Wall', '-Werror', '-fsanitize=address,undefined', '-g',
  '-I' + source + '/include/drm', abi, '-o', work + '/abi-host')
File.write(work + '/abi-host-build.log', out)
abort 'host ABI sanitizer build failed: ' + out unless status.success?
out, status = Open3.capture2e({'ASAN_OPTIONS' => 'halt_on_error=1', 'UBSAN_OPTIONS' => 'halt_on_error=1'}, work + '/abi-host')
File.write(work + '/abi-host-run.log', out)
abort 'host ABI sanitizer execution failed: ' + out unless status.success?
puts 'PASS: target size/alignment/offset expectations; unrelated packing warning remains fatal'
puts 'PASS: host ASan/UBSan unaligned field-access boundary; target executable was not run'
puts 'PASS: actual pkgsrc preserves recipe warning policy after MAKECONF'
puts 'PASS: four actual GCC16 amd64 translation units compile with Werror and visible scoped warnings'
puts 'SCOPE: private object compilation only; no package install or target execution'

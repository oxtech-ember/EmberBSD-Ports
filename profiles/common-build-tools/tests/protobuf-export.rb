#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); scoped package-export failure checks.
require 'fileutils'
require 'json'
require 'open3'
abort 'Usage: protobuf-export.rb NEW_WORK' unless ARGV.length == 1
work = File.expand_path(ARGV[0])
abort 'Output exists.' if File.exist?(work) || File.symlink?(work)
root = File.expand_path('../../..', __dir__)
source = work + '/source'
FileUtils.mkdir_p(source + '/profiles')
FileUtils.mkdir_p(source + '/scripts')
FileUtils.cp(root + '/scripts/prepare-pkgsrc.sh', source + '/scripts/prepare-pkgsrc.sh')
FileUtils.cp_r(root + '/profiles/common-build-tools', source + '/profiles/common-build-tools')
%w[.git upstream pkgsrc probes].each { |p| File.symlink(root + '/' + p, source + '/' + p) }
%w[development-toolchain common-graphics common-media].each { |p| File.symlink(root + '/profiles/' + p, source + '/profiles/' + p) }
records = []
reject = lambda do |name|
  out, err, status = Open3.capture3('sh', source + '/scripts/prepare-pkgsrc.sh', work + '/rejected', 'common-build-tools')
  File.write(work + '/' + name + '.log', out + err)
  abort "Preflight did not reject #{name}" unless status.exitstatus == 2 && !File.exist?(work + '/rejected')
  records << name
end
recipe = source + '/profiles/common-build-tools/recipes/devel/protobuf'
patch = recipe + '/patches/patch-upb_message_copy.c'
link = File.readlink(patch)
File.unlink(patch)
reject.call('missing-protobuf-patch')
File.symlink(root + '/probes/kicad/protobuf/patches/patch-upb_message_copy.c', patch)
reject.call('wrong-protobuf-origin')
File.unlink(patch)
info = File.read(recipe + '/distinfo')
File.write(recipe + '/distinfo', info.lines.reject { |l| l.start_with?('SHA1 (patch-upb_message_copy.c)') }.join)
reject.call('omitted-protobuf-patch-and-hash')
File.symlink(link, patch)
File.write(recipe + '/distinfo', info.sub(/^(SHA1 \(patch-upb_message_copy.c\) = ).+$/, '\\1' + '0' * 40))
reject.call('wrong-protobuf-patch-hash')
File.write(recipe + '/distinfo', info)
File.symlink(root + '/README.md', recipe + '/extra-link')
reject.call('extra-protobuf-link')
File.unlink(recipe + '/extra-link')
File.rename(recipe + '/host-protoc.mk', recipe + '/host-protoc.saved')
reject.call('missing-host-protoc')
File.rename(recipe + '/host-protoc.saved', recipe + '/host-protoc.mk')
%w[PLIST.runtime files/select-package-stage.pl].each do |path|
  File.rename(recipe + '/' + path, recipe + '/' + path + '.saved')
  reject.call('missing-protobuf-' + File.basename(path))
  File.rename(recipe + '/' + path + '.saved', recipe + '/' + path)
end
sdk = source + '/profiles/common-build-tools/recipes/devel/protobuf-devel'
File.rename(sdk + '/PLIST', sdk + '/PLIST.saved')
reject.call('missing-protobuf-sdk-plist')
File.rename(sdk + '/PLIST.saved', sdk + '/PLIST')
File.symlink(root + '/README.md', sdk + '/extra-link')
reject.call('extra-protobuf-sdk-link')
File.unlink(sdk + '/extra-link')
recipe = source + '/profiles/common-build-tools/recipes/devel/abseil'
patch = recipe + '/patches/patch-absl_debugging_CMakeLists.txt'
content = File.binread(patch)
info = File.read(recipe + '/distinfo')
File.unlink(patch)
File.write(recipe + '/distinfo', info.lines.reject { |l| l.start_with?('SHA1 (patch-absl_debugging_CMakeLists.txt)') }.join)
reject.call('omitted-abseil-fix-and-hash')
File.write(patch, content)
File.write(recipe + '/distinfo', info.lines.reject { |l| l.start_with?('SHA1 (patch-absl_base_internal_sysinfo.cc)') }.join)
reject.call('omitted-abseil-canonical-hash')
File.write(recipe + '/distinfo', info)
File.write(patch, content + "\nAltered fixture bytes.\n")
reject.call('altered-abseil-patch')
File.write(patch, content)
File.symlink(root + '/README.md', recipe + '/extra-link')
reject.call('extra-abseil-link')
File.unlink(recipe + '/extra-link')
File.write(work + '/result.json', JSON.pretty_generate({ scope: 'Export preflight only; no build or package installation.', rejected: records }) + "\n")
puts "PASS: #{records.size} protobuf/Abseil preflight refusals."

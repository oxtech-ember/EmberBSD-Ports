#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), exercise the real DMA-BUF loader policy.
require 'digest'
require 'fileutils'
require 'open3'
require 'shellwords'

abort 'usage: dmabuf-providers.rb DMA_BUF_SOURCE RUNNER RUNTIME_MANIFEST NEW_WORK' unless ARGV.length == 4
source, runner, manifest = ARGV.first(3).map { |p| File.realpath(p) }
work = File.expand_path(ARGV[3])
abort 'NEW_WORK must be new and absolute' unless ARGV[3].start_with?('/') && !File.exist?(work)
FileUtils.mkdir_p(work)
# Reuse the actual-callback fixture: it proves return to the caller on refusal,
# not a target loader or renderer. No installed library is changed.
callback_test = File.join(__dir__, 'epoxy-loader-callback.py')
abort 'callback regression failed' unless system(ENV.fetch('PYTHON', 'python3.15'), callback_test, source, "#{work}/callback")
text = File.read(source)
live_call = text.index('REQUIRE(dl_iterate_phdr(loaded_library, (void *)executable) == 0,')
abort 'inventory must precede original BO/context cleanup' unless live_call && live_call < text.index('gbm_bo_unmap(bo, map_data)')
policy = File.read(runner)[/^recorded_library\(\).*?^# End of provider checks[^\n]*\n/m]
abort 'actual live-provider policy missing' unless policy
FileUtils.cp(manifest, "#{work}/runtime-libraries.sha256")
paths = File.readlines(manifest).map { |line| line.split.fetch(1) }
providers = %w[libEGL libGLESv2 libgbm libgallium libLLVM].map do |name|
  paths.find { |path| path.start_with?("/usr/pkg/lib/#{name}") } || abort("manifest lacks #{name}")
end
gbm_backend = '/usr/pkg/lib/gbm/dri_gbm.so'
abort 'accepted DRI backend missing' unless paths.include?(gbm_backend)
base = (providers + [gbm_backend, '/usr/libexec/ld.elf_so']).map { |path| "LOADED: #{path}\n" }.join
script = "set -eu\nbundle=$1\nlogs=$2\n#{policy}\ncheck_live_providers\n"
File.write("#{work}/policy.sh", script)
cases = {
  'recorded-providers' => [base, true, 'PASS:'],
  'unrecorded-gbm-backend' => [base + "LOADED: /usr/pkg/lib/gbm/virtio_gpu_gbm.so\n", false, 'Unrecorded package library'],
  'foreign-provider' => [base + "LOADED: /private/tmp/foreign/libgbm.so\n", false, 'Foreign runtime library'],
  'missing-live-llvm' => [base.lines.reject { |line| line.include?('/libLLVM') }.join, false, 'Missing live provider: libLLVM'],
  'no-inventory' => ['', false, 'Foreign runtime library']
}
cases.each do |name, (inventory, success, diagnostic)|
  logs = "#{work}/#{name}"
  FileUtils.mkdir_p(logs)
  # Explicit parser data fixtures; these are not fabricated target run results.
  File.write("#{logs}/dmabuf.log", inventory)
  out, err, status = Open3.capture3('sh', "#{work}/policy.sh", work, logs)
  File.write("#{logs}/policy.log", out + err)
  abort "failed #{name}" unless status.success? == success && (out + err).include?(diagnostic)
  puts "PASS: #{name} (actual policy, parser fixture only)"
end
File.write("#{work}/inputs.sha256", [source, runner, manifest, callback_test, __FILE__].map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p}\n" }.join)
puts 'PASS: live inventory precedes BO/context cleanup; no target rendering was executed'

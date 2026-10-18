#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), real artifacts and live-policy refusal tests.
require 'digest'
require 'fileutils'
require 'open3'
abort 'usage: wlroots-bundle.rb BUNDLE SYSROOT NEW_WORK' unless ARGV.length == 3
bundle, sysroot = ARGV.first(2).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'NEW_WORK must be new and absolute' unless ARGV.last.start_with?('/') && !File.exist?(work)
FileUtils.mkdir_p(work)
verify = bundle+'/run-mesa-package-tests.sh'

def check(work,name,error,*command)
  out,err,status=Open3.capture3(*command)
  File.write("#{work}/#{name}.log",out+err)
  abort "FAIL: #{name}" unless error.nil? ? status.success? : !status.success? && (out+err).include?(error)
  puts "PASS: #{name}"
end
check(work,'original',nil,'sh',verify,'--verify-sysroot',bundle,sysroot)
copy=work+'/changed-bundle'
FileUtils.cp_r(bundle,copy)
File.open(copy+'/bin/wlroots-render','ab') { |f| f.write('modified ELF') }
check(work,'modified-elf','Bundle hash mismatch: bin/wlroots-render','sh',copy+'/run-wlroots-render.sh',copy,'/dev/dri/card0',work+'/must-not-run')
abort 'target execution reached after ELF corruption' if File.exist?(work+'/must-not-run')
FileUtils.rm_r(copy)
fixture=work+'/sysroot-fixture'
paths=%w[mesa-package-files.sha256 runtime-libraries.sha256].flat_map { |n| File.readlines(bundle+'/'+n).map { |l| l.chomp.split(/  /,2)[1] } }.uniq
paths.each do |path|
  abort 'unsafe fixture path' unless path.start_with?('/usr/pkg/') && !path.split('/').include?('..')
  FileUtils.mkdir_p(File.dirname(fixture+path))
  FileUtils.ln(File.realpath(sysroot+path),fixture+path)
end
File.readlines(bundle+'/mesa-package-links.tsv').each do |line|
  path,target=line.chomp.split("\t",2)
  FileUtils.mkdir_p(File.dirname(fixture+path))
  FileUtils.rm_f(fixture+path)
  FileUtils.ln_s(target,fixture+path)
end
check(work,'original-fixture',nil,'sh',verify,'--verify-sysroot',bundle,fixture)
%w[/usr/pkg/share/xkeyboard-config-2/symbols/us /usr/pkg/lib/libwlroots-0.20.so].each_with_index do |path,i|
  hash=Digest::SHA256.file(sysroot+path).hexdigest
  # Atomic replacement never writes through a source sysroot hard link.
  File.binwrite(fixture+path+'.changed',File.binread(fixture+path)+'changed')
  File.rename(fixture+path+'.changed',fixture+path)
  check(work,"payload-drift-#{i}",'Installed file hash mismatch:','sh',verify,'--verify-sysroot',bundle,fixture)
  abort 'source sysroot changed' unless Digest::SHA256.file(sysroot+path).hexdigest==hash
  FileUtils.rm_f(fixture+path)
  FileUtils.ln(sysroot+path,fixture+path)
end
FileUtils.rm_r(fixture)
# Use the actual policy function with explicit parser data, not a fake target run.
text=File.read(bundle+'/run-wlroots-render.sh')
policy=text[/^recorded_library\(\).*?^# End of provider checks[^\n]*\n/m]
abort 'missing actual provider policy' unless policy
FileUtils.cp(bundle+'/runtime-libraries.sha256',work)
paths=File.readlines(work+'/runtime-libraries.sha256').map { |l| l.split.fetch(1) }
providers=%w[libwlroots-0.20 libwayland-server libxkbcommon libpixman-1 libEGL libGLESv2 libgbm libgallium libLLVM]
inventory=providers.map { |n| paths.find { |p| p.start_with?('/usr/pkg/lib/'+n) } || abort("missing #{n}") }.map { |p| "LOADED: #{p}\n" }.join
File.write(work+'/policy.sh',"set -eu\nbundle=$1\nlogs=$1\n#{policy}\ncheck_live_providers\n")
File.write(work+'/wlroots-render.log',inventory)
check(work,'recorded-live-policy',nil,'sh',work+'/policy.sh',work)
File.open(work+'/wlroots-render.log','a') { |f| f.puts 'LOADED: /usr/pkg/lib/gbm/virtio_gpu_gbm.so' }
check(work,'extra-gbm-provider','Unrecorded package library:','sh',work+'/policy.sh',work)
check(work,'callback',nil,ENV.fetch('PYTHON', 'python3.15'),File.join(__dir__,'epoxy-loader-callback.py'),bundle+'/source/wlroots-render.c',work+'/callback')
puts 'PASS: real payload/link verifier, modified keyboard data/DSO/ELF and actual live policy; no target code executed'

#!/usr/bin/env ruby
# SPDX-License-Identifier: MIT
# Fault injection at allocation and Wayland boundaries around real Mesa functions.
require 'digest'
require 'json'
require 'fileutils'
require 'open3'
require 'shellwords'
abort "Usage: #{$PROGRAM_NAME} MESA_ARCHIVE NEW_OUTPUT" unless ARGV.size==2
archive,work=ARGV.map{|p|File.expand_path(p)}
abort 'Output exists' if File.exist?(work)
FileUtils.mkdir_p(work)
recipe=File.expand_path('../../recipes/graphics/MesaLib',__dir__)
distinfo=File.read(recipe+'/distinfo')
expected=distinfo[/^SHA512 \(mesa-26\.2\.4\.tar\.xz\) = (\h+)$/,1]
abort 'Archive hash mismatch' unless expected && Digest::SHA512.file(archive).hexdigest==expected
patch=recipe+'/patches/patch-src_egl_drivers_dri2_platform__wayland.c'
expected=distinfo[/^SHA1 \(patch-src_egl_drivers_dri2_platform__wayland\.c\) = (\h+)$/,1]
canonical=File.readlines(patch).reject{|line|line.match?(/\$NetBSD.*/)}.join
abort 'Patch hash mismatch' unless expected && Digest::SHA1.hexdigest(canonical)==expected
path='src/egl/drivers/dri2/platform_wayland.c'
text,status=Open3.capture2('tar','-xOf',archive,'mesa-26.2.4/'+path)
abort 'Extraction failed' unless status.success?
%w[baseline patched].each do|variant|
 target=work+'/'+variant+'/'+path
 FileUtils.mkdir_p(File.dirname(target));File.write(target,text)
end
def run(command,log,expected=0,**options)
 out,err,status=Open3.capture3({'ASAN_OPTIONS'=>'halt_on_error=1','UBSAN_OPTIONS'=>'halt_on_error=1'},*command,rlimit_core:0,**options)
 File.write(log,command.shelljoin+"\n"+out+err+"\nexit=#{status.exitstatus} signal=#{status.termsig}\n")
 abort "Unexpected result: #{log}" unless status.exitstatus==expected
 out+err
end
run(['patch','-p0','-i',patch],work+'/patch.log',chdir:work+'/patched')
commands=[]
methods=%w[wait_for_free_buffer get_back_bo update_buffers update_buffers_if_needed image_get_buffers dri2_wl_swap_buffers_with_damage]
cc=ENV.fetch('CC','cc')
%w[baseline patched].each do|variant|
 dir=work+'/'+variant
 source=File.read(dir+'/'+path)
 bodies=methods.map{|name|source[/^static (?:int|void|EGLBoolean)\n#{name}\(.*?^}/m] || abort("Missing #{name}")}
 File.write(dir+'/wayland-methods.inc',bodies.join("\n\n")+"\n")
 FileUtils.cp(__dir__+'/contract.c',dir+'/contract.c')
 %w[normal sanitized].each do|mode|
  flags=mode=='sanitized' ? ['-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer'] : []
  command=[cc,'-std=gnu11','-Wall','-Wextra',*flags,dir+'/contract.c','-o',dir+'/'+mode]
commands << {directory:dir,arguments:command,file:dir+'/contract.c'} if mode=='normal'
run(command,work+"/#{variant}-#{mode}-build.log")
  out=run([dir+'/'+mode],work+"/#{variant}-#{mode}.log",variant=='baseline' ? 1 : 0)
  abort 'Wrong baseline failure' if variant=='baseline' && !out.include?('allocation failure leaves a usable back alias')
 end
end
File.write(work+'/compile_commands.json',JSON.pretty_generate(commands)+"\n")
puts 'PASS: real Mesa Wayland allocation failure, retry and recovery; baseline stale alias reproduced; patched normal/ASan/UBSan pass'

#!/usr/bin/env ruby
# SPDX-License-Identifier: MIT
require 'digest'; require 'fileutils'; require 'json'; require 'open3'; require 'shellwords'
abort "Usage: #{$PROGRAM_NAME} MESA_ARCHIVE NEW_OUTPUT" unless ARGV.size==2
archive,work=ARGV.map { |p| File.expand_path(p) }
abort 'Output exists' if File.exist?(work)
recipe=File.expand_path('../../recipes/graphics/MesaLib',__dir__)
distinfo=File.read(recipe+'/distinfo')
expected=distinfo[/^SHA512 \(mesa-26\.2\.4\.tar\.xz\) = (\h+)$/,1]
abort 'Archive hash mismatch' unless expected && Digest::SHA512.file(archive).hexdigest==expected
name='patch-src_gallium_drivers_v3d_v3d__screen.c'
patch=recipe+'/patches/'+name
expected=distinfo[/^SHA1 \(#{Regexp.escape(name)}\) = (\h+)$/,1]
abort 'Patch hash mismatch' unless expected && Digest::SHA1.hexdigest(File.readlines(patch).reject { |l| l.match?(/\$NetBSD.*/) }.join)==expected
FileUtils.mkdir_p(work)
def run(cmd,log,expected=0,**options)
 out,err,status=Open3.capture3({'ASAN_OPTIONS'=>'halt_on_error=1','UBSAN_OPTIONS'=>'halt_on_error=1'},*cmd,rlimit_core:0,**options)
 File.write(log,cmd.shelljoin+"\n"+out+err+"\nexit=#{status.exitstatus} signal=#{status.termsig}\n")
 abort "Unexpected result: #{log}" unless status.exitstatus==expected
 out+err
end
paths=%w[src/gallium/drivers/v3d/v3d_screen.c src/gallium/drivers/v3d/v3d_bufmgr.c src/util/list.h]
paths.each do |path|
 text,status=Open3.capture2('tar','-xOf',archive,'mesa-26.2.4/'+path)
 abort "Extraction failed: #{path}" unless status.success?
 %w[baseline patched].each do |variant|
  target=work+'/'+variant+'/'+path
  FileUtils.mkdir_p(File.dirname(target));File.write(target,text)
 end
end
run(['patch','-p0','-i',patch],work+'/patch.log',chdir:work+'/patched')
fixed=File.read(work+'/patched/'+paths[0])
mutants={
 'missing-cache-init'=>fixed.sub('if (mtx_init(&screen->bo_cache.lock, mtx_plain) != thrd_success)','if (0)'),
 'ignored-init-failure'=>fixed.sub('if (mtx_init(&screen->bo_cache.lock, mtx_plain) != thrd_success)','if (mtx_init(&screen->bo_cache.lock, mtx_plain) == -99)'),
 'missing-normal-destroy'=>fixed.sub("        mtx_destroy(&screen->bo_cache.lock);\n",''),
 'missing-unwind'=>fixed.sub("fail_handles_mutex:\n        mtx_destroy(&screen->bo_handles_mutex);","fail_handles_mutex:\n"),
 'early-destroy'=>fixed.sub("        v3d_bufmgr_destroy(pscreen);\n        mtx_destroy(&screen->bo_handles_mutex);\n        mtx_destroy(&screen->bo_cache.lock);", "        mtx_destroy(&screen->bo_cache.lock);\n        mtx_destroy(&screen->bo_handles_mutex);\n        v3d_bufmgr_destroy(pscreen);")
}
mutants.each do |variant,text|
 abort "Ineffective mutant #{variant}" if text==fixed
 FileUtils.mkdir_p(work+'/'+variant+'/src/gallium/drivers/v3d')
 File.write(work+'/'+variant+'/'+paths[0],text)
end
commands=[]
(['baseline','patched']+mutants.keys).each do |variant|
 dir=work+'/'+variant
 screen=File.read(dir+'/'+paths[0])
 buf=File.read(work+'/baseline/'+paths[1])
 funcs=[buf[/^static void\nv3d_bo_cache_free_all\([^;{]*\)\n\{.*?^}/m],buf[/^void\nv3d_bufmgr_destroy\(.*?^}/m],screen[/^static void\nv3d_screen_destroy\(.*?^}/m],screen[/^struct pipe_screen \*\nv3d_screen_create\(.*?^}/m]]
 abort 'Missing real function' if funcs.any?(&:nil?)
 File.write(dir+'/lifecycle.inc',funcs.join("\n\n")+"\n")
 FileUtils.cp(work+'/baseline/src/util/list.h',dir+'/list.h')
 FileUtils.cp(__dir__+'/contract.c',dir+'/contract.c')
 %w[normal sanitized].each do |mode|
  [0,1].each do |simulator|
   flags=mode=='sanitized' ? ['-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer'] : []
   output=dir+"/#{mode}-#{simulator}"
   command=[ENV.fetch('CC','cc'),'-std=gnu11','-Wall','-Wextra',*flags,"-DUSE_V3D_SIMULATOR=#{simulator}",*(simulator==0 ? ['-DENABLE_SHADER_CACHE'] : []),dir+'/contract.c','-pthread','-o',output]
   commands << {directory:dir,arguments:command,file:dir+'/contract.c'} if mode=='normal'
   run(command,output+'-build.log')
   text=run([output],output+'.log',variant=='patched' ? 0 : 1)
   abort 'Wrong baseline failure' if variant=='baseline' && !text.include?('screen published without both initialized mutexes')
  end
 end
end
File.write(work+'/compile_commands.json',JSON.pretty_generate(commands)+"\n")
File.write(work+'/results.json',JSON.pretty_generate({source_sha512:Digest::SHA512.file(archive).hexdigest,normal_and_asan_ubsan:'PASS',baseline:'rejects uninitialized cache mutex',mutants:mutants.keys,simulator_variants:[0,1],hardware:'NOT TESTED'})+"\n")
puts 'PASS: real V3D lifecycle, six creation failure stages, normal drain, simulator cleanup, five causal mutants; normal/ASan/UBSan'

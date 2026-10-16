#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
require 'digest';require 'fileutils';require 'json';require 'open3';require 'shellwords'
abort "Usage: #{$PROGRAM_NAME} KCOREADDONS_ARCHIVE NEW_OUTPUT QT_PREFIX" unless ARGV.size==3
archive,work,qt=ARGV.map{|p|File.expand_path(p)}
abort 'Output exists' if File.exist?(work)
recipe=File.expand_path('../../recipes/devel/kf6-kcoreaddons',__dir__)
distinfo=File.read(recipe+'/distinfo')
expected=distinfo[/^SHA512 \(kcoreaddons-6.31.0.tar.xz\) = (\h+)$/,1]
abort 'Archive hash mismatch' unless expected && Digest::SHA512.file(archive).hexdigest==expected
patch=recipe+'/patches/patch-src_lib_io_kdirwatch.cpp'
canonical=File.readlines(patch).reject{|l|l.match?(/\$NetBSD.*/)}.join
expected=distinfo[/^SHA1 \(patch-src_lib_io_kdirwatch.cpp\) = (\h+)$/,1]
abort 'Patch hash mismatch' unless expected && Digest::SHA1.hexdigest(canonical)==expected
FileUtils.mkdir_p(work)
def run(command,log,expected=0,**options)
 out,err,status=Open3.capture3({'ASAN_OPTIONS'=>'halt_on_error=1','UBSAN_OPTIONS'=>'halt_on_error=1'},*command,rlimit_core:0,**options)
 File.write(log,command.shelljoin+"\n"+out+err+"\nexit=#{status.exitstatus} signal=#{status.termsig}\n")
 abort "Unexpected result: #{log}" unless status.exitstatus==expected
 out+err
end
path='src/lib/io/kdirwatch.cpp'
s,status=Open3.capture2('tar','-xOf',archive,'kcoreaddons-6.31.0/'+path);abort 'Extraction failed' unless status.success?
%w[baseline patched].each{|variant|FileUtils.mkdir_p(work+'/'+variant+'/src/lib/io');File.write(work+'/'+variant+'/'+path,s)}
# This retained patch is the accepted nb2 behavior, not pristine upstream.
baseline=__dir__+'/nb2.patch'
abort 'Baseline changed' unless Digest::SHA256.file(baseline).hexdigest=='43f18f06e1cde1c7ad8ced95f97ed1e3c26021d16dee1fb71239877c1bab43e7'
run(['patch','-p0','-F','0','-i',baseline],work+'/baseline-patch.log',chdir:work+'/baseline')
run(['patch','-p0','-F','0','-i',patch],work+'/patch.log',chdir:work+'/patched')
fixed=File.read(work+'/patched/'+path)
mutants={
 'no-budget'=>fixed.sub('watched >= limit.rlim_cur / 2','false'),
 'files-only'=>fixed.sub(' + rlim_t(fsWatcher->directories().size())',''),
 'off-by-one'=>fixed.sub('watched >= limit.rlim_cur / 2','watched > limit.rlim_cur / 2'),
 'no-sticky-stat'=>fixed.sub('if (e->m_mode == StatMode)', 'if (false)'),
 'direct-readd'=>fixed.sub('            // Re-registration must use the same budget and error fallback.'+"\n"+'            addWatch(entry);','            fsWatcher->addPath(entry->path);')
}
mutants.each{|name,text|abort 'Ineffective mutant '+name if text==fixed;FileUtils.mkdir_p(work+'/'+name+'/src/lib/io');File.write(work+'/'+name+'/'+path,text)}
variants=['baseline','patched']+mutants.keys
variants.each do |variant|
 text=File.read(work+'/'+variant+'/'+path)
 methods=%w[useQFSWatch useStat addWatch fswEventReceived].map{|name|text[/^(?:bool|void) KDirWatchPrivate::#{name}\([^;{]*\)\n\{.*?^\}/m] || abort('Missing actual method '+name)}
 File.write(work+'/'+variant+'/kdirwatch-methods.inc',methods.join("\n\n")+"\n")
end
File.write(work+'/CMakeLists.txt',<<~CMAKE)
 cmake_minimum_required(VERSION 3.21)
 project(KDirWatchBudget LANGUAGES CXX)
 set(CMAKE_CXX_STANDARD 17)
 set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
 find_package(Qt6 6.12.0 REQUIRED COMPONENTS Core)
 if(SANITIZE)
   add_compile_options(-fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer)
   add_link_options(-fsanitize=address,undefined)
 endif()
 foreach(variant #{variants.join(' ')})
   add_executable(${variant} "#{__dir__}/contract.cpp")
   target_include_directories(${variant} PRIVATE ${variant})
   target_link_libraries(${variant} PRIVATE Qt6::Core)
 endforeach()
CMAKE
%w[normal sanitized].each do |mode|
 build=work+'/'+mode
 run(['cmake','-S',work,'-B',build,'-DCMAKE_PREFIX_PATH='+qt,'-DCMAKE_BUILD_TYPE=Debug','-DSANITIZE='+(mode=='sanitized' ? 'ON' : 'OFF')],work+'/'+mode+'-configure.log')
 run(['cmake','--build',build,'--parallel','2'],work+'/'+mode+'-build.log')
 variants.each do |variant|
  out=run([build+'/'+variant],work+'/'+mode+'-'+variant+'.log',variant=='patched' ? 0 : 1)
  expected = %w[no-sticky-stat direct-readd].include?(variant) ? 'live Stat fallback has one accounted entry' : 'exact files-plus-directories budget must select Stat'
  abort 'Wrong causal failure: '+variant if variant != 'patched' && !out.include?('FAIL: '+expected)
  abort 'Sanitizer failure: '+variant if out.match?(/ERROR: AddressSanitizer|runtime error:/)
 end
end
File.write(work+'/results.json',JSON.pretty_generate({baseline:'accepted nb2',normal_asan_ubsan:'PASS',mutants:mutants.keys,scope:'Actual method control flow. Resource limit, watcher and event boundaries doubled. No real filesystem-event claim.'})+"\n")
puts 'PASS: real KDirWatch budget/fallback methods, nb2 causal baseline, five mutants, normal/ASan/UBSan'

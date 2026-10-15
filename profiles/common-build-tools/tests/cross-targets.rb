# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), explicit target selection without mixed runtimes.
require 'tmpdir'
require 'fileutils'
require 'open3'
bmake=ARGV.fetch(0){abort 'Usage: ruby cross-targets.rb BMAKE'}
root=File.expand_path('../../..',__dir__)
Dir.mktmpdir('ember-cross-targets-') do |d|
  tools=%w[gcc g++ cpp gcc-ar gcc-nm gcc-ranlib ar as ld nm objcopy objdump ranlib readelf strip]
  %w[compiler/bin os/bin sysroot/usr/pkg/gcc16/lib].each{|p|FileUtils.mkdir_p(d+'/'+p)}
  %w[aarch64--netbsd x86_64--netbsd].each do |triplet|
    tools.each do |name|
      path=d+'/compiler/bin/'+triplet+'-'+name
      File.write(path,"#!/bin/sh\ncase \"$1\" in -dumpmachine) echo #{triplet};; -dumpfullversion) echo 16.2.0;; esac\n")
      File.chmod(0755,path)
    end
    File.write(d+'/os/bin/'+triplet+'-install',"#!/bin/sh\nexit 0\n")
    File.chmod(0755,d+'/os/bin/'+triplet+'-install')
    FileUtils.mkdir_p(d+'/sysroot/usr/pkg/gcc16/lib/gcc/'+triplet+'/16.2.0')
    File.write(d+'/sysroot/usr/pkg/gcc16/lib/gcc/'+triplet+'/16.2.0/crtbeginS.o','fixture')
  end
  File.write(d+'/sysroot/usr/pkg/gcc16/lib/libstdc++.so.7','fixture')
  %w[aarch64 amd64].each do |target|
    triplet=target=='amd64' ? 'x86_64--netbsd' : 'aarch64--netbsd'
    out,err,st=Open3.capture3('sh',root+'/profiles/common-build-tools/cross/prepare-tools.sh','--target',target,d+'/compiler',d+'/os',d+'/tools-'+target)
    abort out+err unless st.success?
    abort 'Wrong tool composition' unless File.symlink?(d+'/tools-'+target+'/bin/'+triplet+'-gcc')
  end
  File.write(d+'/Makefile',<<~MAKE)
    BSD_PKG_MK=yes
    PKGPATH=devel/ember-target-fixture
    EMBERBSD_CROSS_TOOLS=#{d}/compiler
    EMBERBSD_CROSS_SYSROOT=#{d}/sysroot
    EMBERBSD_CROSS_HOST_PREFIX=#{d}/os
    .include "#{root}/profiles/common-build-tools/cross/mk.conf"
  MAKE
  read=->(*args){out,err,st=Open3.capture3(bmake,'-f',d+'/Makefile',*args);abort out+err unless st.success?;out.strip}
  abort 'Default target changed' unless read.call('-v','CROSS_MACHINE_ARCH')=='aarch64'
  abort 'amd64 selected the wrong machine' unless read.call('EMBERBSD_CROSS_TARGET=amd64','-v','CROSS_MACHINE_ARCH')=='x86_64'
  abort 'amd64 selected ARM compiler' unless read.call('EMBERBSD_CROSS_TARGET=amd64','-v','CC').end_with?('/x86_64--netbsd-gcc')
  abort 'amd64 has profile failures' unless read.call('EMBERBSD_CROSS_TARGET=amd64','-v','PKG_FAIL_REASON').empty?
  abort 'Unknown target accepted' unless read.call('EMBERBSD_CROSS_TARGET=mips','-v','PKG_FAIL_REASON').include?('Unsupported cross target')
  abort 'Mixed architecture accepted' unless read.call('EMBERBSD_CROSS_TARGET=amd64','CROSS_MACHINE_ARCH=aarch64','-v','PKG_FAIL_REASON').include?('selected cross target')
  deps=read.call('EMBERBSD_CROSS_TARGET=amd64','EMBERBSD_GCC16_RUNTIME_PROVIDER=runtime','-v','DEPENDS')
  abort 'Runtime-only image depends on a compiler' unless deps.include?('gcc16-runtime>=16.2.0nb1:../../lang/gcc16-runtime') && !deps.include?('gcc16>=')
  runtime_args=%w[EMBERBSD_CROSS_TARGET=amd64 EMBERBSD_GCC16_RUNTIME_PROVIDER=runtime PKGPATH=lang/gcc16-runtime]
  abort 'Runtime package depends on itself' unless read.call(*runtime_args,'-v','DEPENDS').empty?
  abort 'Runtime package rejected its own provider' unless read.call(*runtime_args,'-v','PKG_FAIL_REASON').empty?
  abort 'Runtime package accepted compiler provider' unless read.call('PKGPATH=lang/gcc16-runtime','-v','PKG_FAIL_REASON').include?('requires the runtime provider')
  abort 'Conflicting gcc16-libs provider accepted' unless read.call('PKGPATH=lang/gcc16-libs','-v','PKG_FAIL_REASON').include?('not a provider')
  abort 'Invalid runtime provider accepted' unless read.call('EMBERBSD_GCC16_RUNTIME_PROVIDER=invalid','-v','PKG_FAIL_REASON').include?('single GCC16 runtime provider')
  File.unlink(d+'/sysroot/usr/pkg/gcc16/lib/gcc/x86_64--netbsd/16.2.0/crtbeginS.o')
  abort 'ARM runtime accepted for amd64' unless read.call('EMBERBSD_CROSS_TARGET=amd64','-v','PKG_FAIL_REASON').include?('GCC16 CRT and runtime')
end
puts 'PASS: ARM default and explicit amd64 tools/runtime stay separate; unsupported and mixed targets fail closed'

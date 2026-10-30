#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), real pkgtools/bmake fixture regression.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'rbconfig'
require 'shellwords'
require 'tmpdir'
abort 'Usage: package-targets.rb VERIFIED_DISTFILES NEW_RECEIPT_DIR' unless ARGV.size == 2
distfiles, receipt = ARGV.map { |p| File.expand_path(p) }
abort 'Receipt path already exists' if File.exist?(receipt)
%w[BMAKE PKG_CREATE].each { |key| abort "Set #{key}" if ENV[key].to_s.empty? }
check = File.expand_path('package.rb', __dir__)
toolkit = File.expand_path('../..', __dir__)
record = File.readlines(File.join(toolkit,'sources.tsv')).map { |l| l.chomp.split("\t") }.find { |r| r[0]=='x11/plasma6-plasma-workspace' }
archive = File.join(distfiles,record.fetch(1))
abort 'Verified Workspace source required' unless Digest::SHA256.file(archive).hexdigest == record.fetch(2)
FileUtils.mkdir_p(receipt)
File.write(File.join(receipt,'space-before.txt'),Open3.capture2('df','-k',receipt,'/System/Volumes/Data')[0])
count = failures = 0

def run(command, log, **options)
  out,status = Open3.capture2e(*command,**options)
  File.write(log,"$ #{command.shelljoin}\n#{out}\nexit=#{status.exitstatus}; signal=#{status.termsig}\n")
  [out,status]
end

def elf(machine, klass: 2, endian: 1)
  # Header-only fixture; no executable code, program headers, or Qt plugin.
  data = "\0".b * 64
  data[0,7] = "\x7fELF".b + [klass,endian,1].pack('C*')
  data[18,2] = [machine].pack('v')
  data
end

def metadata(arch)
  {'OPSYS'=>'NetBSD','OS_VERSION'=>'11.0','MACHINE_ARCH'=>arch,'OBJECT_FMT'=>'ELF'}
end

Dir.mktmpdir('plasma-volume-targets-') do |work|
  File.write(File.join(receipt,'temporary-path.txt'),"#{work}\n")
  makeconf = File.join(work,'mk.conf'); File.write(makeconf,'')
  create = ENV.fetch('PKG_CREATE')
  run([create,'-V'],File.join(receipt,'pkg-create-version.log'))
  run([ENV.fetch('BMAKE'),'-V','MAKE_VERSION'],File.join(receipt,'bmake-version.log'))
  real_elf = nil
  if ENV['TARGET_CC'] || ENV['TARGET_SYSROOT']
    abort 'Set TARGET_CC and TARGET_SYSROOT together' unless ENV['TARGET_CC'] && ENV['TARGET_SYSROOT']
    cc = ENV.fetch('TARGET_CC')
    triplet,status = run([cc,'-dumpmachine'],File.join(receipt,'target-triplet.log'))
    abort 'Use the actual amd64 NetBSD cross compiler' unless status.success? && triplet.match?(/\Ax86_64-.*netbsd/)
    run([cc,'--version'],File.join(receipt,'target-compiler-version.log'))
    source = File.join(work,'fixture.c'); dso = File.join(work,'libvolumeplugin.so')
    File.write(source,"/* DSO fixture only. No Qt plugin or audio implementation. */\nint volume_target_fixture(void) { return 7; }\n")
    _,status = run([cc,"--sysroot=#{ENV.fetch('TARGET_SYSROOT')}",'-std=c11','-O2','-fPIC','-shared','-nostdlib','-Wl,-soname,libvolumeplugin.so',source,'-o',dso],File.join(receipt,'target-dso-compile.log'))
    abort 'Actual cross GCC DSO fixture compile failed' unless status.success?
    real_elf = File.binread(dso)
    FileUtils.cp(source,File.join(receipt,'target-fixture.c'))
    File.write(File.join(receipt,'target-fixture.sha256'),"#{Digest::SHA256.file(dso).hexdigest}  GCC-produced DSO fixture\n#{Digest::SHA256.file(cc).hexdigest}  #{cc}\n")
  end
  fixture = lambda do |name, arch, modifications|
    directory = File.join(work,name)
    pkgsrc = File.join(directory,'pkgsrc'); paqt = File.join(directory,'paqt'); pa = File.join(directory,'pa')
    packages = File.join(directory,'packages'); database = File.join(directory,'private-pkgdb')
    FileUtils.mkdir_p([packages,database,File.join(paqt,'lib/pkgconfig'),File.join(paqt,'include/KF6/KF6PulseAudioQt/PulseAudioQt')])
    File.write(File.join(paqt,'include/KF6/KF6PulseAudioQt/PulseAudioQt/Context'),"Fixture header\n")
    File.write(File.join(paqt,'lib/pkgconfig/KF6PulseAudioQt.pc'),"prefix=/usr/pkg\nincludedir=${prefix}/include/KF6/KF6PulseAudioQt\n")
    qml = File.join(pa,'qt6/qml/org/kde/plasma/private/volume'); FileUtils.mkdir_p(qml)
    File.write(File.join(qml,'qmldir'),"module org.kde.plasma.private.volume\nplugin volumeplugin\n")
    plugin = File.join(qml,'libvolumeplugin.so')
    File.binwrite(plugin,modifications.fetch(:elf,elf(arch=='aarch64' ? 183 : 62)))
    packagespec = {'pulseaudio-qt'=>'pulseaudio-qt-1.9.0','plasma6-plasma-pa'=>'plasma6-plasma-pa-6.8.2'}
    %w[x11/plasma6-plasma-workspace audio/pulseaudio-qt audio/plasma6-plasma-pa].each do |recipe|
      path = File.join(pkgsrc,recipe); FileUtils.mkdir_p(path)
      values = metadata(arch).merge(modifications.fetch(:make,{}).fetch(recipe,{}))
      depends = recipe=='x11/plasma6-plasma-workspace' ? 'plasma6-plasma-pa>=6.8.2:../../audio/plasma6-plasma-pa' : ''
      File.write(File.join(path,'Makefile'),values.map { |k,v| "#{k}=#{v}\n" }.join+"DEPENDS=#{depends}\n")
    end
    packagespec.each do |recipe,package|
      prefix = recipe=='pulseaudio-qt' ? paqt : pa
      plist = Dir.chdir(prefix) { Dir['**/*'].select { |p| File.file?(p) }.sort.join("\n")+"\n" }
      list = File.join(pkgsrc,'audio',recipe,'PLIST'); File.write(list,plist)
      description = File.join(directory,'description'); File.write(description,"Fixture only: not a built Plasma package.\n")
      info = File.join(directory,"#{recipe}.build-info")
      values = metadata(arch).merge(modifications.fetch(:archive,{}).fetch(recipe,{}))
      text = values.map { |k,v| "#{k}=#{v}\n" }.join
      text += "MACHINE_ARCH=#{arch}\n" if modifications[:duplicate_archive] == recipe
      File.write(info,text)
      if modifications[:empty_archive] == recipe
        list = File.join(directory,'empty-plist'); File.write(list,"@comment Empty payload negative fixture\n")
      end
      command = [create,'-K',database,'-p',prefix,'-I','/usr/pkg','-f',list,'-c',description,'-d',description,'-B',info,File.join(packages,"#{package}.tgz")]
      _,status = run(command,File.join(receipt,"#{name}-#{recipe}-create.log"))
      abort 'Native pkg_create fixture failed' unless status.success?
    end
    File.unlink(plugin) if modifications[:missing_plugin]
    File.binwrite(plugin,elf(62)) if modifications[:repair_staged_elf]
    if %w[aarch64-default amd64-explicit amd64-gcc16-dso-fixture].include?(name)
      snapshot = File.join(receipt,'fixture-archives',name); FileUtils.mkdir_p(snapshot)
      FileUtils.cp(Dir[File.join(packages,'*.tgz')],snapshot)
    end
    [pkgsrc,paqt,pa,distfiles,packages]
  end
  audit = lambda do |name,arch,options,expected=nil,modifications={}|
    paths = fixture.call(name,arch,modifications)
    command = [{'BMAKE'=>ENV.fetch('BMAKE'),'MAKECONF'=>makeconf},RbConfig.ruby,check,*options,*paths]
    out,status = Open3.capture2e(*command)
    File.write(File.join(receipt,"#{name}-audit.log"),"#{command.inspect}\n#{out}\nexit=#{status.exitstatus}\n")
    good = expected ? !status.success? && out.include?(expected) : status.success?
    count += 1
    unless good
      failures += 1
      warn "FAIL: #{name}: expected #{expected || 'success'}; got #{out.lines.first&.strip}"
    end
  end
  audit.call('aarch64-default','aarch64',[])
  audit.call('aarch64-default-mixed-bmake','aarch64',[],'Wrong target MACHINE_ARCH',make:{'x11/plasma6-plasma-workspace'=>{'MACHINE_ARCH'=>'x86_64'}})
  audit.call('aarch64-default-mixed-archive','aarch64',[],'Wrong target MACHINE_ARCH',archive:{'pulseaudio-qt'=>{'MACHINE_ARCH'=>'x86_64'}})
  audit.call('aarch64-explicit','aarch64',['--target','aarch64'])
  audit.call('amd64-explicit','x86_64',['--target','amd64'])
  audit.call('amd64-default-rejected','x86_64',[],'Wrong target MACHINE_ARCH')
  audit.call('wrong-amd64-selector','aarch64',['--target','amd64'],'Wrong target MACHINE_ARCH')
  audit.call('wrong-aarch64-selector','x86_64',['--target','aarch64'],'Wrong target MACHINE_ARCH')
  %w[x11/plasma6-plasma-workspace audio/pulseaudio-qt audio/plasma6-plasma-pa].each_with_index do |recipe,i|
    audit.call("mixed-bmake-#{i}",'x86_64',['--target','amd64'],'Wrong target MACHINE_ARCH',make:{recipe=>{'MACHINE_ARCH'=>'aarch64'}})
  end
  {'OPSYS'=>'Darwin','OS_VERSION'=>'10.0','OBJECT_FMT'=>'MACHO','MACHINE_ARCH'=>''}.each do |key,value|
    audit.call("wrong-metadata-#{key}",'x86_64',['--target','amd64'],"Wrong target #{key}",make:{'audio/plasma6-plasma-pa'=>{key=>value}})
  end
  %w[pulseaudio-qt plasma6-plasma-pa].each do |recipe|
    audit.call("mixed-archive-#{recipe}",'x86_64',['--target','amd64'],'Wrong target MACHINE_ARCH',archive:{recipe=>{'MACHINE_ARCH'=>'aarch64'}})
  end
  audit.call('duplicate-archive-metadata','x86_64',['--target','amd64'],'Wrong target MACHINE_ARCH',duplicate_archive:'plasma6-plasma-pa')
  audit.call('wrong-machine','x86_64',['--target','amd64'],'Wrong ELF machine',elf:elf(183))
  audit.call('wrong-class','x86_64',['--target','amd64'],'Unsupported ELF class',elf:elf(62,klass:1))
  audit.call('wrong-endian','x86_64',['--target','amd64'],'Unsupported ELF byte order',elf:elf(62,endian:2))
  audit.call('truncated-plugin','x86_64',['--target','amd64'],'Truncated ELF header',elf:"\x7fELF".b)
  audit.call('non-elf-plugin','x86_64',['--target','amd64'],'Not an ELF plugin',elf:'plain data'*8)
  audit.call('empty-plugin','x86_64',['--target','amd64'],'Truncated ELF header',elf:'')
  audit.call('missing-plugin','x86_64',['--target','amd64'],'Volume plugin file is missing',missing_plugin:true)
  audit.call('wrong-archived-plugin','x86_64',['--target','amd64'],'Wrong ELF machine',elf:elf(183),repair_staged_elf:true)
  audit.call('empty-package','x86_64',['--target','amd64'],'archive payload differs from PLIST',empty_archive:'plasma6-plasma-pa')
  selector_paths = fixture.call('selector-fixtures','aarch64',{})
  {'unknown'=>['--target','riscv64'],'empty'=>['--target',''],'missing'=>['--target'],'repeated'=>['--target','amd64','--target','aarch64']}.each do |name,args|
    out,status = Open3.capture2e({'BMAKE'=>ENV.fetch('BMAKE'),'MAKECONF'=>makeconf},RbConfig.ruby,check,*selector_paths,*args)
    File.write(File.join(receipt,"#{name}-selector.log"),out)
    count += 1
    expected = case name
               when 'unknown', 'empty' then 'Unsupported target'
               when 'missing' then 'missing argument: --target'
               else 'Target is repeated'
               end
    if status.success? || !out.include?(expected)
      failures += 1; warn "FAIL: #{name} selector"
    end
  end
  audit.call('amd64-gcc16-dso-fixture','x86_64',['--target','amd64'],nil,elf:real_elf) if real_elf
end
File.write(File.join(receipt,'inputs.sha256'),[__FILE__,check,File.join(toolkit,'sources.tsv'),archive].map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p}\n" }.join)
File.write(File.join(receipt,'scope.txt'),"Native pkgtools archives with fixture Makefiles evaluated by real bmake.\nHeader-only ELF fixtures and an optional real GCC-built DSO fixture. No Qt plugin or complete package build.\nNo native package database installation or target execution. Temporary fixture trees removed.\nFull target audio package and runtime acceptance remain pending.\n")
File.write(File.join(receipt,'space-after.txt'),Open3.capture2('df','-k',receipt,'/System/Volumes/Data')[0])
puts "#{count} fixture cases, #{failures} failures"
abort 'Package target regression failed' unless failures.zero?
puts 'PASS: fixture-only package target/metadata/ELF rejection matrix'

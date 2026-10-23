#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), pinned ConsoleKit source regression.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'
require 'tmpdir'
abort 'Usage: process-query.rb VERIFIED_ARCHIVE NEW_RECEIPT_DIR' unless ARGV.size==2
archive, receipt=ARGV.map { |p| File.expand_path(p) }
abort 'Receipt path already exists' if File.exist?(receipt)
%w[CC SANITIZER_CC PKG_CONFIG CPPCHECK DIGEST].each { |k| abort "Set #{k}" if ENV[k].to_s.empty? }
tests=File.expand_path(__dir__)
toolkit=File.expand_path('../..',tests)
recipe=File.expand_path('../../../pkgsrc/sysutils/consolekit',toolkit)
root=File.expand_path('../../..',toolkit)
expected='f3f4a424f2a4fbb67696b4011caf2fd4c02e5e67c24ef1c86cecb2301bccdba4'
abort 'Archive SHA256 mismatch' unless Digest::SHA256.file(archive).hexdigest==expected
FileUtils.mkdir_p(receipt)
def command(argv,log,chdir:nil,success:true)
  out,status=Open3.capture2e(*argv,**(chdir ? {chdir:chdir} : {}))
  File.write(log,"$ #{argv.shelljoin}\n#{out}")
  abort "Command failed: #{log}" if success && !status.success?
  [out,status]
end
def function(source,name)
  m=source.match(/^#{Regexp.escape(name)}\s*\(.*?^\}\n/m)
  abort "Cannot extract #{name}" unless m
  source[0...m.begin(0)].lines.last+m[0]
end
verifier=File.join(root,'upstream/pkgsrc/mk/checksum/checksum.awk')
command(['awk','-f',verifier,'--',File.join(recipe,'distinfo'),File.basename(archive)],File.join(receipt,'archive-checksum.log'),chdir:File.dirname(archive))
patches=File.readlines(File.join(recipe,'distinfo')).filter_map { |l| l[/^SHA1 \((patch-[^)]+)\)/,1] }
patches.each do |name|
  command(['awk','-f',verifier,'--','-p',File.join(recipe,'distinfo'),File.join(recipe,'patches',name)],File.join(receipt,"checksum-#{name}.log"))
end
cflags=Shellwords.split(command([ENV['PKG_CONFIG'],'--cflags','glib-2.0'],File.join(receipt,'host-cflags.log'))[0])
libs=Shellwords.split(command([ENV['PKG_CONFIG'],'--libs','glib-2.0'],File.join(receipt,'host-libs.log'))[0])
command([ENV['PKG_CONFIG'],'--modversion','glib-2.0'],File.join(receipt,'host-glib-version.log'))
flags=['-std=c11','-Wall','-Werror',*Shellwords.split(ENV.fetch('HOST_CFLAGS','')),*cflags]
%w[CC SANITIZER_CC CPPCHECK].each { |k| command([ENV[k],'--version'],File.join(receipt,"#{k.downcase}-version.log")) }
File.write(File.join(receipt,'space-before.txt'),Open3.capture2('df','-k',receipt,'/System/Volumes/Data')[0])
Dir.mktmpdir('consolekit-process-query-') do |work|
  File.write(File.join(receipt,'temporary-path.txt'),"#{work}\nAutomatically removed after this test.\n")
  pristine=File.join(work,'pristine'); FileUtils.mkdir(pristine)
  command(['tar','-xf',archive,'--strip-components=1','-C',pristine],File.join(receipt,'extract.log'))
  FileUtils.cp(File.join(pristine,'COPYING'),File.join(receipt,'upstream-COPYING'))
  source_path='src/ck-sysdeps-netbsd.c'
  FileUtils.cp(File.join(pristine,source_path),File.join(receipt,'upstream-ck-sysdeps-netbsd.c'))
  %w[baseline candidate].each do |mode|
    tree=File.join(work,mode); FileUtils.cp_r(pristine,tree)
    patches.each do |name|
      patch=File.join(recipe,'patches',name)
      next if mode=='baseline' && name=='patch-src_ck-sysdeps-netbsd.c'
      command(['patch','-f','-N','-F','0','-p0','-i',patch],File.join(receipt,"#{mode}-#{name}.log"),chdir:tree)
    end
    source=File.read(File.join(tree,source_path))
    struct=source[/^struct _CkProcessStat\n.*?^\};\n/m] or abort 'Cannot extract private stat'
    names=%w[get_kinfo_proc2 stat2proc ck_process_stat_new_for_unix_pid ck_process_stat_free ck_unix_pid_get_env_hash ck_unix_pid_get_uid]
    extracted=struct+"\n"+names.map { |n| function(source,n) }.join("\n")
    File.write(File.join(tree,'extracted.c'),extracted)
    File.write(File.join(receipt,"#{mode}-extracted.c"),extracted)
    FileUtils.cp(File.join(tests,'process-query.c'),File.join(tree,'process-query.c'))
    modeflags=flags+(mode=='candidate' && source.include?('start_time_usec') ? ['-DCHECK_START_USEC=1'] : [])
    command([ENV['CC'],*modeflags,'process-query.c',*libs,'-o','fixture'],File.join(receipt,"#{mode}-compile.log"),chdir:tree)
    out,status=command([File.join(tree,'fixture'),*(source.include?('struct kinfo_proc2 snapshot;') ? [] : ['baseline'])],File.join(receipt,"#{mode}-run.log"),success:false)
    puts "#{mode}: #{out.lines.last&.strip}"
    abort 'Baseline did not reproduce missing query guards' if mode=='baseline' && status.success?
    abort 'Candidate causal regression failed' if mode=='candidate' && !status.success?
    analysisflags=modeflags.reject { |f| f=='-Werror' }
    command([ENV['CC'],*analysisflags,'-fanalyzer','-c','process-query.c','-o','analysis.o'],File.join(receipt,"#{mode}-gcc-analyzer.log"),chdir:tree)
    command([ENV['SANITIZER_CC'],*analysisflags,'--analyze','-Xanalyzer','-analyzer-output=text','process-query.c'],File.join(receipt,"#{mode}-clang-analyzer.log"),chdir:tree)
    command([ENV['CPPCHECK'],'--quiet','--enable=warning,performance,portability','--template={file}:{line}:{severity}:{id}:{message}','--std=c11','--platform=unix64',*cflags.select { |f| f.start_with?('-I','-D') },'process-query.c'],File.join(receipt,"#{mode}-cppcheck.log"),chdir:tree)
    next unless mode=='candidate'
    command([ENV['SANITIZER_CC'],*modeflags,'-fsanitize=address,undefined','-fno-omit-frame-pointer','process-query.c',*libs,'-o','fixture-asan'],File.join(receipt,'candidate-asan-compile.log'),chdir:tree)
    command([File.join(tree,'fixture-asan')],File.join(receipt,'candidate-asan-run.log'))
    # Each mutation removes one production guard from the actual extracted code.
    mutations={
      'length'=>['len != sizeof snapshot','0'],
      'pid'=>['snapshot.p_pid != pid','0'],
      'uvalid'=>['snapshot.p_uvalid == 0','0'],
      'state'=>['(snapshot.p_realstat != SACTIVE && snapshot.p_realstat != SSTOP)','0'],
      'start-seconds'=>['snapshot.p_ustart_sec == 0','0'],
      'start-microseconds'=>['snapshot.p_ustart_usec >= 1000000','0'],
      'failure-free'=>['g_free (proc);','/* missing free */'],
      'failure-output'=>['memset (p, 0, sizeof *p);','/* missing output initialization */'],
      'invalid-uid'=>['return (uid_t) -1;','return 0;'],
      'start-usec-retention'=>['P->start_time_usec = p.p_ustart_usec;','P->start_time_usec = 0;']
    }
    mutations.each do |name,(from,to)|
      abort "Mutation not found: #{name}" unless extracted.include?(from)
      File.write(File.join(tree,'extracted.c'),extracted.sub(from,to))
      command([ENV['CC'],*modeflags,'process-query.c',*libs,'-o','mutant'],File.join(receipt,"mutation-#{name}-compile.log"),chdir:tree)
      _,result=command([File.join(tree,'mutant')],File.join(receipt,"mutation-#{name}-run.log"),success:false)
      abort "Mutation survived: #{name}" if result.success?
    end
  end
end
files=[archive,__FILE__,File.join(tests,'process-query.c'),File.join(recipe,'Makefile'),File.join(recipe,'distinfo'),*Dir[File.join(recipe,'patches/patch-*')]]
File.write(File.join(receipt,'inputs.sha256'),files.map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p}\n" }.join)
File.write(File.join(receipt,'scope.txt'),"Pinned actual ConsoleKit functions with real native GLib and controlled sysctl/KVM transport.\nHost model is not a target kinfo_proc2 ABI test.\nTarget full TU awaits real cross-GLib headers/configuration.\nNo backend activation, session authority, D-Bus runtime or hardware acceptance.\nTemporary source and executables were removed.\n")
File.write(File.join(receipt,'space-after.txt'),Open3.capture2('df','-k',receipt,'/System/Volumes/Data')[0])
puts 'PASS: process-query host causal regression; target TU remains pending'

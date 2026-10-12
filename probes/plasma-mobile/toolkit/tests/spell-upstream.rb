#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), cross-build unchanged upstream test consumers.
require 'fileutils'
require 'digest'
abort 'Usage: spell-upstream.rb ASPELL_SOURCE HUNSPELL_SOURCE DISTFILES CROSS_TOOLS SYSROOT NEW_OUTPUT' unless ARGV.size == 6
aspell, hunspell, distfiles, tools, sysroot, out = ARGV.map { |p| File.expand_path(p) }
Dir.mkdir(out)
fixtures = {
  'aspell6-en-2018.04.16-0.tar.bz2' => 'f11071e74b0c0753f4afabf024941a5c3a96bafe3879211ebd47bc34e76fbd2f',
  'IPC-System-Simple-1.30.tar.gz' => '22e6f5222b505ee513058fdca35ab7a1eab80539b98e5ca4a923a70a8ae9ba9e'
}
fixtures.each do |archive, sha|
  abort "Fixture hash mismatch: #{archive}" unless Digest::SHA256.file(distfiles + '/' + archive).hexdigest == sha
end
FileUtils.cp_r(aspell+'/test',out+'/aspell-test')
FileUtils.cp_r(hunspell+'/tests',out+'/hunspell-tests')
FileUtils.mkdir(out+'/aspell-dict')
system('tar','-xjf',distfiles+'/aspell6-en-2018.04.16-0.tar.bz2','--strip-components=1','-C',out+'/aspell-dict') || abort('extract')
body=File.read(hunspell+'/tests/Makefile.am')[/^TESTS\s*=\s*(.*?)(?:\n\n)/m,1]
tests=body.delete("\\").split
raise 'Unexpected upstream inventory' unless tests.size==174
File.write(out+'/hunspell-tests.list',tests.join("\n")+"\n")
gcc=tools+'/bin/aarch64--netbsd-gcc'
gxx=tools+'/bin/aarch64--netbsd-g++'
flags=["--sysroot=#{sysroot}","-B#{sysroot}/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/",'-O2',"-I#{sysroot}/usr/pkg/include"]
ld=["-L#{sysroot}/usr/pkg/lib","-L#{sysroot}/usr/pkg/gcc16/lib",'-Wl,-rpath,/usr/pkg/lib','-Wl,-rpath,/usr/pkg/gcc16/lib']
[['valid','wide_test_valid.c',[]],['invalid','wide_test_invalid.c',[]],['secure','wide_test_invalid.c',['-DASPELL_ENCODE_SETTING_SECURE']]].each do |name,file,extra|
 obj=out+"/aspell-test/wide_test_#{name}.o"
 system(gcc,*flags,*extra,'-c',aspell+'/test/'+file,'-o',obj) || abort('compile')
 system(gxx,*flags,obj,*ld,'-laspell','-o',out+"/aspell-test/wide_test_#{name}") || abort('link')
 File.unlink(obj)
end
%w[gh1032 gh1058].each do |name|
 system(gxx,*flags,hunspell+"/tests/#{name}.cxx",*ld,'-lhunspell-1.7','-o',out+"/hunspell-tests/#{name}") || abort('Hunspell regression build')
end
FileUtils.mkdir(out+'/test-perl')
system('tar','-xzf',distfiles+'/IPC-System-Simple-1.30.tar.gz','--strip-components=1','-C',out+'/test-perl') || abort('Perl fixture extract')
FileUtils.cp(File.join(__dir__, 'spell-runtime.sh'),out+'/run.sh')
FileUtils.cp(File.join(__dir__, 'diff-trailing-space.sh'),out+'/diff-trailing-space.sh')

files=Dir.glob(out+'/**/*').select { |p| File.file?(p) }.sort
File.write(out+'/SHA256SUMS',files.map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p.delete_prefix(out+'/')}\n" }.join)
puts "Prepared #{tests.size} Hunspell upstream cases and Aspell upstream checks"

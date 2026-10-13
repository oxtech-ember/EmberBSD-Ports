# Origin: EmberBSD pinned installer desktop bundle, prepared with AI assistance.
# SPDX-License-Identifier: BSD-2-Clause
require 'json'
require 'digest'
require 'fileutils'
require 'open3'
abort 'Usage: ruby bundle.rb new-output native-dhcpcd-gtk3-package.tgz' unless ARGV.size==2
output=File.expand_path(ARGV[0]); leaf=File.expand_path(ARGV[1])
abort 'Output already exists' if File.exist?(output)
lock=JSON.parse(File.read(__dir__+'/packages.json'))
FileUtils.mkdir_p(output+'/All')
lock.fetch('packages').sort_by{|p|p['local'] ? 0 : 1}.each do |p|
  name=p.fetch('file');abort 'Unsafe package filename' unless name.match?(/\A[A-Za-z0-9_+.-]+\.tgz\z/) && !name.start_with?('.')
  path=output+'/All/'+name
  if p['local']
    FileUtils.cp(leaf,path)
  else
    _,err,status=Open3.capture3('curl','-fsSL','--retry','2','--max-time','120','-o',path,lock.fetch('repository')+name)
    abort err unless status.success?
  end
  abort "Changed package: #{name}" unless File.size(path)==p.fetch('size') && Digest::SHA512.file(path).hexdigest==p.fetch('sha512')
end
names=lock['packages'].map{|p|p['file']}
lock.fetch('roots').each{|n|abort 'Missing root package' unless names.include?(n+'.tgz')}
File.write(output+'/ROOTS',lock['roots'].join("\n")+"\n")
File.write(output+'/SHA512',lock['packages'].sort_by{|p|p['file']}.map{|p|"SHA512 (#{p['file']}) = #{p['sha512']}"}.join("\n")+"\n")
# bsdtar is supplied by macOS and EmberBSD. Exclude host extended attributes.
archive=output+'/desktop-xfce.tar.xz'
_,err,status=Open3.capture3({'COPYFILE_DISABLE'=>'1'},'tar','--no-xattrs','--no-acls','--uid','0','--gid','0','-cJf',archive,'-C',output,'All','ROOTS','SHA512')
abort err unless status.success?
puts "SHA512 (desktop-xfce.tar.xz) = #{Digest::SHA512.file(archive).hexdigest}"

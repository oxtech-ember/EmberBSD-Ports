# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Compare full packaged manuals and actual rules.
require 'open3';require 'digest'
abort 'Usage: speech-manpages.rb SOURCE ARCHIVE PACKAGE' unless ARGV.size == 3
src,archive,pkg=ARGV
make=ENV.fetch('GMAKE')
{'speech-dispatcher'=>'src/server','spd-say'=>'src/clients/say','spd-conf'=>'src/api/python/speechd_config'}.each do |name,dir|
 original,status=Open3.capture2('tar','-xOf',archive,'speech-dispatcher-0.12.1/'+dir+'/'+name+'.1');abort unless status.success?
 installed,status=Open3.capture2('tar','-xOf',pkg,'man/man1/'+name+'.1');abort unless status.success?
 abort "Manual changed: #{name}" unless installed==original
 puts "PASS: #{name} shipped manpage, SHA256 #{Digest::SHA256.hexdigest(original)}"
 # Force the target program's timestamp logically, not by changing the work tree.
 target={'speech-dispatcher'=>'speech-dispatcher','spd-say'=>'spd-say','spd-conf'=>'buildconfig.py'}[name]
 cross,st=Open3.capture2e(make,'-C',src+'/'+dir,'-n','-W',target,'EMBERBSD_DIST_MANPAGES=yes',name+'.1')
 abort "Cross page regeneration: #{name}: #{cross}" unless st.success? && !cross.include?('LC_ALL=C')
 native,st=Open3.capture2e(make,'-C',src+'/'+dir,'-n','-W',target,name+'.1')
 abort "Native generation lost: #{name}: #{native}" unless st.success? && native.include?('LC_ALL=C') && native.include?('help2man')
 puts "PASS: #{name} actual make rules retain native regeneration and avoid target execution on host"
end

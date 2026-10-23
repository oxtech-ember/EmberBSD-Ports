#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Actual bounded local-source validator cases.
require 'fileutils'
require 'json'
require 'open3'
require 'digest'
abort 'Usage: source-contract.rb NEW_OUTPUT' unless ARGV.size==1
work=File.expand_path(ARGV[0]);abort 'Select a new absolute output directory' unless ARGV[0].start_with?('/')&&!File.exist?(work);Dir.mkdir(work,0700)
service=File.realpath(__dir__);toolkit=File.dirname(service);ports=File.expand_path('../../..',toolkit);recipe='sysutils/ember-plasma-session';good=work+'/good';recipes=good+'/recipes';FileUtils.mkdir_p(recipes+'/'+recipe)
FileUtils.cp_r(ports+'/pkgsrc/'+recipe+'/.',recipes+'/'+recipe,preserve:true)
FileUtils.mkdir_p(recipes+'/devel/source');File.write(recipes+'/devel/source/Makefile',"DISTNAME=source-1\n");File.write(recipes+'/devel/source/PLIST',"share/source\n");File.write(recipes+'/devel/source/distinfo',"BLAKE2s (source-1.tar.gz) = #{'1'*64}\nSHA512 (source-1.tar.gz) = #{'2'*128}\nSize (source-1.tar.gz) = 1 bytes\n");File.write(good+'/sources.tsv',"devel/source\tsource-1.tar.gz\t#{'3'*64}\thttps://example.invalid/source-1.tar.gz\n");File.write(good+'/source-owners.tsv',"#{recipe}\t#{recipe}\tlocal\t-\n")
rows=[]
run=lambda do |name,path,expected=nil|
 out,err,status=Open3.capture3('/bin/sh',toolkit+'/validate.sh',path,path+'/recipes');File.write(work+'/'+name+'.stdout',out);File.write(work+'/'+name+'.stderr',err);rows<<{name:name,exit:status.exitstatus,stdout_sha256:Digest::SHA256.hexdigest(out),stderr_sha256:Digest::SHA256.hexdigest(err)}
 if expected
  raise "#{name}: unrelated success/failure #{status.inspect} #{out}#{err}" unless status.exited?&&status.exitstatus==2&&(out+err).include?(expected)
 else
  raise "#{name}: #{out}#{err}" unless status.success?
 end
end
run.call('valid',good)
negative=lambda do |name,expected,&change|
 path=work+'/'+name;FileUtils.cp_r(good,path,preserve:true);change.call(path);run.call(name,path,expected)
end
files=->(p){p+'/recipes/'+recipe+'/files'}
negative.call('missing-source','Missing or external canonical local source'){|p|File.unlink(files.(p)+'/plasma-service.pl')}
File.write(work+'/external','external source')
negative.call('external-source','Missing or external canonical local source'){|p|f=files.(p)+'/plasma-service.pl';File.unlink(f);File.symlink(work+'/external',f)}
negative.call('linked-copy','Missing or external canonical local source'){|p|f=files.(p)+'/plasma-service.pl';FileUtils.cp(f,p+'/copy.pl');File.unlink(f);File.symlink('../../../../copy.pl',f)}
negative.call('external-files-directory','External local source directory'){|p|FileUtils.remove_entry(files.(p));File.symlink(files.(good),files.(p))}
negative.call('external-recipe-parent','External local source directory'){|p|FileUtils.remove_entry(p+'/recipes/sysutils');File.symlink(good+'/recipes/sysutils',p+'/recipes/sysutils')}
negative.call('external-recipe','Missing toolkit recipe'){|p|FileUtils.remove_entry(p+'/recipes/'+recipe);File.symlink(good+'/recipes/'+recipe,p+'/recipes/'+recipe)}
negative.call('extra-source-file','Unexpected local source files'){|p|File.write(files.(p)+'/extra.pl',"extra\n")}
negative.call('build-enabled','Local recipe must use empty DISTFILES and NO_BUILD=yes'){|p|f=p+'/recipes/'+recipe+'/Makefile';File.write(f,File.read(f).sub(/^NO_BUILD=.*\n/,''))}
negative.call('nonempty-distfiles','Local recipe must use empty DISTFILES and NO_BUILD=yes'){|p|f=p+'/recipes/'+recipe+'/Makefile';File.write(f,File.read(f).sub(/^DISTFILES=.*$/, 'DISTFILES=foreign.tar.gz'))}
negative.call('local-archive','Local recipe must not select an archive'){|p|File.open(p+'/sources.tsv','a'){|f|f.puts "#{recipe}\tforeign.tar.gz\t#{'4'*64}\thttps://example.invalid/foreign.tar.gz"}}
negative.call('foreign-local-owner','Invalid local source-owner binding'){|p|File.open(p+'/source-owners.tsv','a'){|f|f.puts "devel/source\tdevel/source\tlocal\t-"}}
negative.call('implicit-local-owner','Toolkit recipe has no manifest row'){|p|File.write(p+'/source-owners.tsv','')}
negative.call('package-local-owner','Missing toolkit source owner'){|p|File.write(p+'/source-owners.tsv',"#{recipe}\t#{recipe}\tpackage\t-\n")}
negative.call('upstream-digest','Invalid archive digest'){|p|f=p+'/recipes/devel/source/distinfo';File.write(f,File.read(f).sub('2'*128,'bad'))}
File.write(work+'/receipt.json',JSON.pretty_generate({status:'PASS',cases:rows,validator_sha256:Digest::SHA256.file(toolkit+'/validate.sh').hexdigest,scope:'Actual metadata validator with tiny labelled manifests; no archive verification, package build or target claim.'})+"\n");puts "PASS: #{rows.size} bounded local-source metadata cases"

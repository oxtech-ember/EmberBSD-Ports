#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted). Exercise the production verifier.
require 'digest'
require 'fileutils'
require 'open3'
abort 'usage: mesa-generators.rb DIGEST SEALED_TOOLS NEW_WORK' unless ARGV.size == 3
digest, sealed = ARGV.first(2).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'Use a new absolute work directory' unless ARGV.last.start_with?('/') && !File.exist?(work)
FileUtils.mkdir_p(work)
verify = File.expand_path('../../../pkgsrc/graphics/MesaLib/verify-mesa-generators.sh', __dir__)
# Small model files exercise parsing and binding; the actual sealed tools are
# also verified against the exact recipe interface without running any tool.
source = work + '/source'
FileUtils.mkdir_p(source)
File.write(source + '/VERSION', "26.2.5\n")
require 'json'
origin = JSON.parse(File.read(sealed + '/receipt.json')).fetch('source')
File.readlines(sealed + '/interface.sha256').each do |line|
    _, path = line.split
    FileUtils.mkdir_p(File.dirname(source + '/' + path))
    FileUtils.cp(origin + '/' + path, source + '/' + path)
end
patch = File.expand_path('../../../pkgsrc/graphics/MesaLib/patches/patch-src_imagination_common_pvr__iface.h', __dir__)
out, status = Open3.capture2e('patch', '-f', '-N', '-F', '0', '-p0', '-d', source, '-i', patch)
abort out unless status.success?
checks = 0
run = lambda do |name, tools, src, valid|
    out, status = Open3.capture2e('sh', verify, digest, tools, src)
    File.write(work + '/' + name + '.log', out)
    abort "Unexpected result: #{name}" unless status.success? == valid
    checks += 1
end
run.call('real-tools', sealed, source, true)
fixture = work + '/fixture'
FileUtils.mkdir_p(fixture + '/bin')
File.write(fixture + '/FORMAT', "ember-mesa-generators-1\n")
File.write(fixture + '/receipt.json', "{}\n")
FileUtils.cp(sealed + '/interface.sha256', fixture + '/interface.sha256')
%w[mesa_clc vtn_bindgen2 pco_clc].each do |name|
    File.write(fixture + '/bin/' + name, "never executed\n")
    File.chmod(0755, fixture + '/bin/' + name)
end
manifest = Dir.glob(fixture + '/**/*').select { |p| File.file?(p) }.sort.map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p.delete_prefix(fixture + '/')}\n" }.join
File.write(fixture + '/installed.sha256', manifest)
run.call('model-positive', fixture, source, true)
{
    'missing-tool' => -> { File.unlink(fixture + '/bin/pco_clc') },
    'changed-tool' => -> { File.write(fixture + '/bin/pco_clc', 'changed') },
    'missing-manifest-entry' => -> { File.write(fixture + '/installed.sha256', manifest.lines.reject { |l| l.end_with?("bin/pco_clc\n") }.join) },
    'duplicate-tool' => -> { File.write(fixture + '/installed.sha256', manifest + manifest.lines.find { |l| l.end_with?("bin/pco_clc\n") }) },
    'bad-hash' => -> { File.write(fixture + '/installed.sha256', manifest.sub(/[0-9a-f]/, 'x')) },
    'traversal' => -> { File.write(fixture + '/installed.sha256', manifest + "#{'0' * 64}  ../secret\n") },
    'changed-abi' => -> { File.write(source + '/src/compiler/nir/nir.h', 'changed') },
    'changed-last-tool-no-lf' => -> {
        row = manifest.lines.find { |l| l.end_with?("bin/pco_clc\n") }
        File.write(fixture + '/installed.sha256', (manifest.lines.reject { |l| l == row }.join + row).chomp)
        File.write(fixture + '/bin/pco_clc', 'changed')
    },
    'changed-last-interface-no-lf' => -> {
        iface = File.read(fixture + '/interface.sha256').chomp
        File.write(fixture + '/interface.sha256', iface)
        hash = Digest::SHA256.file(fixture + '/interface.sha256').hexdigest
        File.write(fixture + '/installed.sha256', manifest.lines.map { |l| l.end_with?("interface.sha256\n") ? "#{hash}  interface.sha256\n" : l }.join)
        File.write(source + '/' + iface.lines.last.split.last, 'changed')
    },
    'wrong-version' => -> { File.write(source + '/VERSION', "26.2.5\n") }
}.each do |name, mutate|
    backup = work + '/save'
    FileUtils.cp_r(fixture, backup)
    FileUtils.cp_r(source, work + '/save-source')
    mutate.call
    run.call(name, fixture, source, false)
    if name.end_with?('no-lf')
        old = work + '/verifier-old-final-line.sh'
        File.write(old, File.read(verify).sub(' || [ -n "$expected$file$extra" ]', ''))
        out, status = Open3.capture2e('sh', old, digest, fixture, source)
        File.write(work + '/' + name + '-causal.log', out)
        abort "Old verifier did not expose #{name}" unless status.success?
    end

    FileUtils.rm_r(fixture)
    FileUtils.mv(backup, fixture)
    FileUtils.rm_r(source)
    FileUtils.mv(work + '/save-source', source)
end
# This causal mutation removes the byte comparison in the actual verifier.
mutant = work + '/verifier-without-hash.sh'
File.write(mutant, File.read(verify).sub('[ "${actual##* }" = "$expected" ] || fail "changed file: $file"', ':'))
File.write(fixture + '/bin/pco_clc', 'changed')
_, status = Open3.capture2e('sh', mutant, digest, fixture, source)
abort 'Causal guard mutation did not admit changed bytes' unless status.success?
puts "PASS: #{checks} production receipt/interface checks and causal missing-hash control"

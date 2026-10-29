#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted host-only generator capability regression.
require 'tmpdir'
require 'fileutils'
require 'digest'
require 'open3'
require 'json'
root = File.expand_path('..', __dir__)
verifier = root + '/../../pkgsrc/graphics/MesaLib/verify-mesa-generators.sh'
checks = 0
Dir.mktmpdir('mesa-generator-profiles-', '/tmp') do |d|
  tools = d + '/tools'; source = d + '/source'
  FileUtils.mkdir_p([tools + '/bin', source + '/src/compiler/nir', source + '/src/util'])
  File.write(source + '/VERSION', "26.2.5\n")
  File.write(source + '/src/compiler/nir/nir.h', 'interface fixture')
  File.write(source + '/src/util/u_dynarray.h', 'shared generator interface')
  File.write(tools + '/FORMAT', "ember-mesa-generators-2\n")
  File.write(tools + '/HOST', "#{`uname -s`.strip}/#{`uname -m`.strip}/clang\n")
  File.write(tools + '/PROFILES', "intel\n")
  File.write(tools + '/receipt.json', JSON.generate('profiles' => ['intel']))
  File.write(tools + '/interface.sha256',
    "#{Digest::SHA256.file(source + '/src/compiler/nir/nir.h').hexdigest}  src/compiler/nir/nir.h\n" +
    "#{Digest::SHA256.file(source + '/src/util/u_dynarray.h').hexdigest}  src/util/u_dynarray.h\n")
  %w[mesa_clc vtn_bindgen2].each do |name|
    File.write(tools + '/bin/' + name, "#!/bin/sh\nexit 99\n")
    File.chmod(0755, tools + '/bin/' + name)
  end
  digest = d + '/digest'
  File.write(digest, "#!/bin/sh\n[ \"$1\" = SHA256 ] || exit 2\nresult=$(/usr/bin/shasum -a 256 \"$2\") || exit 1\nprintf '%s\n' \"${result%% *}\"\n")
  File.chmod(0755, digest)
  manifest = lambda do
    files = Dir.glob(tools + '/**/*').select { |p| File.file?(p) && !p.end_with?('/installed.sha256') }.sort
    File.write(tools + '/installed.sha256', files.map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p.delete_prefix(tools + '/')}\n" }.join)
  end
  fakebin = d + '/fake-bin'
  FileUtils.mkdir_p(fakebin)
  File.write(fakebin + '/uname', "#!/bin/sh\ncase \"$1\" in -s) printf '%s\\n' \"$TEST_UNAME_S\";; -m) printf '%s\\n' \"$TEST_UNAME_M\";; *) exit 2;; esac\n")
  File.chmod(0755, fakebin + '/uname')
  check = lambda do |name, profile, valid, fake_host = nil|
    env = {'PATH' => fake_host ? fakebin + ':' + ENV.fetch('PATH') : ENV.fetch('PATH')}
    env['TEST_UNAME_S'], env['TEST_UNAME_M'] = fake_host if fake_host
    out, status = Open3.capture2e(env, '/bin/sh', verifier, digest, tools, source, profile)
    abort "FAIL #{name}: #{out}" unless status.success? == valid
    checks += 1
  end
  manifest.call
  check.call('Intel needs no PCO tool', 'intel', true)
  File.write(tools + '/HOST', "Linux/x86_64/clang\n")
  manifest.call
  check.call('v2 Linux host ABI accepted', 'intel', true, ['Linux', 'x86_64'])
  File.write(tools + '/HOST', "Darwin/arm64/gcc\n")
  manifest.call
  check.call('v2 Darwin host ABI accepted', 'intel', true, ['Darwin', 'arm64'])
  File.write(tools + '/HOST', "Linux/aarch64/clang\n")
  manifest.call
  check.call('v2 wrong host ABI rejected', 'intel', false, ['Linux', 'x86_64'])
  File.write(tools + '/FORMAT', "ember-mesa-generators-1\n")
  File.unlink(tools + '/HOST')
  manifest.call
  check.call('legacy v1 remains accepted', 'intel', true)
  File.write(tools + '/FORMAT', "ember-mesa-generators-2\n")
  File.write(tools + '/HOST', "#{`uname -s`.strip}/#{`uname -m`.strip}/clang\n")
  manifest.call
  if ENV['BMAKE']
    mk = d + '/Makefile'
    File.write(mk, <<~MAKE)
      ECHO=echo
      MV=mv
      SH=/bin/sh
      WRKDIR=#{d}
      WRKSRC=#{source}
      TOOLS_DIGEST=#{digest}
      EMBERBSD_MESA_GENERATORS=#{tools}
      _EMBERBSD_MESA_GENERATOR_PROFILES=intel
      _EMBERBSD_MESA_GENERATOR_NAMES=mesa_clc vtn_bindgen2
      .include "#{root}/../../pkgsrc/graphics/MesaLib/mesa-generators.mk"
    MAKE
    native = d + '/.meson-generators-native'
    out, status = Open3.capture2e(ENV['BMAKE'], '-r', '-m', '/', '-C', root + '/../../pkgsrc/graphics/MesaLib', '-f', mk, native, 'emberbsd-mesa-generators-check')
    abort "FAIL production native-file target: #{out}" unless status.success?
    text = File.read(native)
    abort 'Intel native file requires PCO' if text.include?('pco_clc')
    %w[mesa_clc vtn_bindgen2].each { |name| abort "Missing #{name} native binding" unless text.include?("#{name} = '#{tools}/bin/#{name}'") }
    checks += 1
  end

  check.call('Intel seal cannot supply PowerVR', 'powervr', false)
  check.call('Unknown capability fails', 'unknown', false)
  original = File.read(tools + '/bin/mesa_clc')
  File.write(tools + '/bin/mesa_clc', 'changed')
  check.call('Changed tool is rejected', 'intel', false)
  File.write(tools + '/bin/mesa_clc', original)
  File.chmod(0755, tools + '/bin/mesa_clc')
  File.write(tools + '/installed.sha256', File.read(tools + '/installed.sha256').lines.reject { |l| l.end_with?("PROFILES\n") }.join)
  check.call('Unsealed capabilities fail', 'intel', false)
  manifest.call
  File.write(tools + '/PROFILES', "intel,powervr\n")
  manifest.call
  check.call('PowerVR still needs PCO tool', 'powervr', false)
  File.write(tools + '/bin/pco_clc', "#!/bin/sh\nexit 99\n")
  File.chmod(0755, tools + '/bin/pco_clc')
  manifest.call
  check.call('Combined seal supplies both', 'intel,powervr', true)
  File.unlink(tools + '/PROFILES')
  manifest.call
  check.call('Legacy seal supplies PowerVR', 'powervr', true)
  check.call('Legacy seal cannot claim Intel', 'intel', false)
end
puts "PASS: #{checks} production generator profile checks; tools are never executed"

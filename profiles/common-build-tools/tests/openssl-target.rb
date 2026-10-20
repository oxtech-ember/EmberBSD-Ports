# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), real pkgsrc and upstream Configure checks.
require 'fileutils'
require 'open3'
require 'json'
require 'digest'
require 'shellwords'
require 'time'
abort 'Usage: ruby openssl-target.rb EXPORTED_PKGSRC MAKECONF DISTFILE NEW_WORK' unless ARGV.length == 4
pkgsrc, makeconf, archive, work = ARGV.map { |p| File.expand_path(p) }
abort 'Output must be new' if File.exist?(work)
FileUtils.mkdir_p(work)
bmake = ENV.fetch('BMAKE', 'bmake')
profile = File.expand_path('..', __dir__)
records = []
run = lambda do |label, argv, env = {}, dir = work, redact: false|
  out, err, status = Open3.capture3(env, *argv, chdir: dir)
  File.write(work + '/' + label + '.log', redact ? "Configure environment filtered in memory; proxy and HOME values omitted.\n" : out + err)
  records << {label: label, argv: argv, directory: dir, exit: status.exitstatus}
  File.write(work + '/commands.json', JSON.pretty_generate(records) + "\n")
  abort "#{label} failed: #{err.lines.last(5).join}" unless status.success?
  out
end
abort 'macOS host required for causal Darwin detection' unless run.call('uname', ['uname', '-s']).strip == 'Darwin'
expected = File.read(pkgsrc + '/security/openssl/distinfo')[/^SHA512 \(#{Regexp.escape(File.basename(archive))}\) = (\h+)$/, 1]
abort 'Missing archive checksum' unless expected && Digest::SHA512.file(archive).hexdigest == expected
# Copy only this recipe. Other package sources and mk are read-only symlinks.
shadow = work + '/pkgsrc'
FileUtils.mkdir_p(shadow + '/security')
Dir.children(pkgsrc).each do |name|
  File.symlink(pkgsrc + '/' + name, shadow + '/' + name) unless name == 'security'
end
Dir.children(pkgsrc + '/security').each do |name|
  next if name == 'openssl'
  File.symlink(pkgsrc + '/security/' + name, shadow + '/security/' + name)
end
FileUtils.cp_r(pkgsrc + '/security/openssl', shadow + '/security/openssl')
recipe = shadow + '/security/openssl'
patch = File.read(profile + '/patches/pkgsrc-cross-packages.patch')[/^--- a\/security\/openssl\/Makefile\n.*?(?=^--- a\/|\z)/m]
if patch
  File.write(work + '/openssl-recipe.patch', patch)
  run.call('patch', ['patch', '--batch', '--fuzz=0', '-p1', '-i', work + '/openssl-recipe.patch'], {}, shadow)
end
vars = %w[OPSYS MACHINE_ARCH CONFIG_SHELL CONFIGURE_SCRIPT CONFIGURE_ARGS PERL5 PKG_FAIL_REASON CROSS_DESTDIR EMBERBSD_CROSS_TOOLS]
metadata = lambda do |label, *args|
  argv = [bmake, '-C', recipe, 'MAKECONF=' + makeconf, 'WRKOBJDIR=' + work + '/objects', 'PACKAGES=' + work + '/packages', *args]
  argv += vars.flat_map { |v| ['-V', '${' + v + '}'] }
  out = run.call(label, argv)
  values = out.lines.map(&:chomp)
  abort 'Unexpected metadata output' unless values.length == vars.length
  vars.zip(values).to_h
end
amd64 = metadata.call('metadata-amd64')
# Preserve the actual recipe environment's configure inputs, without proxies,
# HOME, or shared cwrapper configuration and its shared log/output paths.
env_out = run.call('metadata-env', [bmake, '-C', recipe, 'MAKECONF=' + makeconf, 'WRKOBJDIR=' + work + '/objects', '-V', '${_CONFIGURE_SCRIPT_ENV:NCC=*}'], redact: true)
env = Shellwords.split(env_out).filter_map { |s| s.split('=', 2) if s.match?(/\A[A-Za-z_][A-Za-z_0-9]*=/) }.to_h
keys = %w[MACHINE SYSTEM RELEASE BUILD CFLAGS CPPFLAGS LDFLAGS PERL LANG LC_ALL]
env = env.select { |k, _| keys.include?(k) }
cc = amd64.fetch('EMBERBSD_CROSS_TOOLS') + '/bin/x86_64--netbsd-gcc'
sysroot = amd64.fetch('CROSS_DESTDIR')
abort 'Real target compiler/sysroot required' unless File.executable?(cc) && File.directory?(sysroot + '/usr/include')
FileUtils.mkdir_p(work + '/bin')
File.write(work + '/bin/cc', "#!/bin/sh\nexec #{Shellwords.escape(cc)} --sysroot=#{Shellwords.escape(sysroot)} \"$@\"\n")
File.chmod(0755, work + '/bin/cc')
perl = amd64.fetch('PERL5')
env['PATH'] = [work + '/bin', File.dirname(perl), '/opt/homebrew/bin', '/usr/bin', '/bin'].join(':')
env['CC'] = nil
base_args = Shellwords.split(amd64.fetch('CONFIGURE_ARGS')).reject { |x| x.start_with?('BSD-') }
configure = lambda do |label, script, args|
  dir = work + '/' + label
  FileUtils.mkdir_p(dir)
  run.call(label + '-extract', ['tar', '-xzf', archive, '-C', dir])
  src = dir + '/openssl-3.6.5'
  run.call(label + '-configure', [perl, script, *args], env, src)
  query = 'print JSON::PP::encode_json({config=>{map {$_=>$configdata::config{$_}} qw(target CC CFLAGS CPPFLAGS LDFLAGS)},target=>{map {$_=>$configdata::target{$_}} qw(asm_arch perlasm_scheme shared_target)}})'
  data = JSON.parse(run.call(label + '-data', [perl, '-I.', '-Mconfigdata', '-MJSON::PP', '-e', query], env, src))
  File.write(work + '/' + label + '.json', JSON.pretty_generate(data) + "\n")
  [src, data]
end
_, baseline = configure.call('baseline', './config', base_args)
abort 'Causal baseline did not detect Darwin despite NetBSD environment' unless baseline.dig('config', 'target').start_with?('darwin')
puts "RED: original config detects #{baseline.dig('config', 'target')} despite SYSTEM=NetBSD MACHINE=amd64"
abort 'amd64 did not select explicit upstream BSD target' unless amd64['CONFIGURE_SCRIPT'] == './Configure' && Shellwords.split(amd64['CONFIGURE_ARGS']).include?('BSD-x86_64')
abort 'Assembly or shared build disabled' if Shellwords.split(amd64['CONFIGURE_ARGS']).any? { |x| %w[no-asm no-shared].include?(x) }
abort 'Configure did not use native Perl' unless amd64['CONFIG_SHELL'] == perl
candidate_src, candidate = configure.call('amd64', './Configure', Shellwords.split(amd64.fetch('CONFIGURE_ARGS')))
abort 'Wrong amd64 Configure result' unless candidate.dig('config', 'target') == 'BSD-x86_64' && candidate.dig('target', 'asm_arch') == 'x86_64' && candidate.dig('target', 'perlasm_scheme') == 'elf'
abort 'Darwin flags survived' if candidate.to_json.match?(/darwin|(?:^|[ \"\\])-(?:arch|dynamiclib|isysroot)\b/i)
abort 'Shared build disabled' unless candidate.dig('target', 'shared_target').include?('bsd')
arm = metadata.call('metadata-aarch64', 'EMBERBSD_CROSS_TARGET=aarch64')
abort 'Wrong ARM recipe target' unless arm['CONFIGURE_SCRIPT'] == './Configure' && Shellwords.split(arm['CONFIGURE_ARGS']).include?('BSD-aarch64')
_, arm_config = configure.call('aarch64', './Configure', Shellwords.split(arm.fetch('CONFIGURE_ARGS')))
abort 'ARM assembly target changed' unless arm_config.dig('target', 'asm_arch') == 'aarch64' && arm_config.dig('config', 'target') == 'BSD-aarch64'
unknown = metadata.call('metadata-unknown', 'MACHINE_ARCH=unsupported')
abort 'Unknown OpenSSL cross target accepted' unless unknown['PKG_FAIL_REASON'].include?('Unsupported OpenSSL NetBSD cross architecture')
native = metadata.call('metadata-native', 'USE_CROSS_COMPILE=no', 'OPSYS=Darwin', 'OS_VERSION=27.0', 'MACHINE_ARCH=aarch64')
abort 'Native Darwin selection changed' unless Shellwords.split(native['CONFIGURE_ARGS']).include?('darwin64-arm64-cc')
# Compile one unmodified upstream TU through the real generated Makefile.
gmake = ENV.fetch('GMAKE', 'gmake')
run.call('amd64-headers', [gmake, '-j1', 'build_generated'], env, candidate_src)
object = 'crypto/aes/libcrypto-lib-aes_cfb.o'
run.call('amd64-tu', [gmake, '-j1', object], env, candidate_src)
bytes = File.binread(candidate_src + '/' + object, 20)
abort 'TU is not amd64 ELF64 little-endian' unless bytes.start_with?("\x7fELF".b) && bytes.getbyte(4) == 2 && bytes.getbyte(5) == 1 && bytes.byteslice(18, 2).unpack1('v') == 62
triple = run.call('compiler-triple', [cc, '-dumpmachine']).strip
version = run.call('compiler-version', [cc, '-dumpfullversion']).strip
abort 'Common GCC16 target compiler required' unless triple == 'x86_64--netbsd' && version.start_with?('16.')
receipt = {at: Time.now.utc.iso8601, archive: {path: archive, sha512: expected}, metadata: {amd64: amd64, aarch64: arm, unknown: unknown, native: native}, configure: {baseline: baseline, amd64: candidate, aarch64: arm_config}, compiler: {path: cc, triple: triple, version: version}, object: {path: candidate_src + '/' + object, sha256: Digest::SHA256.file(candidate_src + '/' + object).hexdigest}, scope: 'Real pkgsrc metadata, upstream Configure and one real amd64 TU. ARM is configuration only; the amd64 sysroot correctly fails its ARM runtime gate. No full package, target execution, runtime or native package acceptance.'}
File.write(work + '/receipt.json', JSON.pretty_generate(receipt) + "\n")
puts 'PASS: explicit BSD amd64/ARM Configure, intact assembly/shared mode, native selection and unknown rejection; actual amd64 ELF TU'

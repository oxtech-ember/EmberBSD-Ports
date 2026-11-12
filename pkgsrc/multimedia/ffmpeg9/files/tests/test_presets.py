#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Draft: causal FFmpeg CLI preset search in an isolated moved prefix."""
import argparse, os, subprocess, tempfile, uuid
from contextlib import ExitStack
from pathlib import Path
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--prefix', type=Path, required=True)
p.add_argument('--producer-prefix', type=Path, required=True)
p.add_argument('--expect', choices=('old', 'new'), required=True)
a = p.parse_args()
if not a.prefix.is_absolute() or not a.producer_prefix.is_absolute(): p.error('prefix paths must be absolute')
if a.prefix.resolve() == a.producer_prefix.resolve(): p.error('moved prefix must differ from producer')
exe = a.prefix/'bin/ffmpeg9'
with tempfile.TemporaryDirectory(prefix='ffmpeg-preset-test-') as d, ExitStack() as cleanup:
    root=Path(d); datadir=a.prefix/'share/ffmpeg9'; home=root/'home'; envdir=root/'env'
    home.mkdir(); envdir.mkdir(); datadir.mkdir(parents=True,exist_ok=True)
    env={k:v for k,v in os.environ.items() if not k.startswith('DYLD_') and k not in ('HOME','FFMPEG_DATADIR','AVCONV_DATADIR')}
    env['HOME']=str(home)
    link=root/'ffmpeg-link'; link.symlink_to(exe)
    def invoke(opt, name, overrides=None, binary=exe):
        e=dict(env); e.update(overrides or {})
        return subprocess.run([str(binary),'-hide_banner','-f','lavfi','-i','color=size=16x16:rate=1','-frames:v','1','-c:v','mpeg4',opt,name,'-f','null','-'],env=e,text=True,capture_output=True)
    def preset(path,marker):
        with path.open('x') as f: f.write(marker+'\n')
        cleanup.callback(path.unlink, missing_ok=True)
        return path
    def check(opt,name,marker,overrides=None,binary=exe,default=False):
        r=invoke(opt,name,overrides,binary)
        assert r.returncode != 0, (opt,name,r.stdout,r.stderr)
        found=marker in r.stderr
        assert found == (a.expect=='new' if default else True), (opt,name,r.returncode,r.stderr)
    version=subprocess.run([str(exe),'-version'],env=env,text=True,capture_output=True)
    assert version.returncode == 0 and 'ffmpeg version' in version.stdout, version.stderr
    baseline=invoke('-metadata','comment=ember-baseline')
    assert baseline.returncode == 0, baseline.stderr
    token='emberpreset'+uuid.uuid4().hex
    producer_data=a.producer_prefix/'share/ffmpeg9'
    for ext in ('ffpreset','avpreset'):
        for stem in (token, 'mpeg4-'+token):
            assert not (producer_data/(stem+'.'+ext)).exists(), 'producer contains fixture name'
    preset(datadir/(token+'.ffpreset'),'bad syntax default_ffpreset_marker')
    preset(datadir/('mpeg4-'+token+'.avpreset'),'codec_avpreset_marker=5')
    preset(datadir/(token+'.avpreset'),'generic_avpreset_marker=5')
    check('-vpre',token,'default_ffpreset_marker',default=True)
    check('-pre:v',token,'codec_avpreset_marker',default=True)
    check('-pre:v',token,'codec_avpreset_marker',binary=link,default=True)
    (datadir/('mpeg4-'+token+'.avpreset')).unlink()
    check('-pre:v',token,'generic_avpreset_marker',default=True)
    (datadir/(token+'.ffpreset')).unlink()
    preset(datadir/('mpeg4-'+token+'.ffpreset'),'bad syntax codec_ffpreset_marker')
    check('-vpre',token,'codec_ffpreset_marker',default=True)
    missing=invoke('-vpre',token+'missing')
    assert missing.returncode != 0 and 'not found' in missing.stderr, missing.stderr
    preset(envdir/(token+'.ffpreset'),'bad syntax env_ffpreset_marker')
    check('-vpre',token,'env_ffpreset_marker',{'FFMPEG_DATADIR':str(envdir)})
    preset(envdir/('mpeg4-'+token+'.avpreset'),'env_avpreset_marker=5')
    check('-pre:v',token,'env_avpreset_marker',{'AVCONV_DATADIR':str(envdir)})
    (home/'.ffmpeg').mkdir(); (home/'.avconv').mkdir()
    preset(home/'.ffmpeg'/(token+'.ffpreset'),'bad syntax home_ffpreset_marker')
    preset(home/'.avconv'/('mpeg4-'+token+'.avpreset'),'home_avpreset_marker=5')
    check('-vpre',token,'home_ffpreset_marker'); check('-pre:v',token,'home_avpreset_marker')
    check('-vpre',token,'env_ffpreset_marker',{'FFMPEG_DATADIR':str(envdir)})
    check('-pre:v',token,'env_avpreset_marker',{'AVCONV_DATADIR':str(envdir)})
    explicit=preset(root/'explicit.ffpreset','bad syntax explicit_ffpreset_marker')
    check('-fpre',str(explicit),'explicit_ffpreset_marker')
    # Valid default .ffpreset changes output metadata after relocation.
    valid_name=token+'valid'
    for ext in ('ffpreset','avpreset'):
        for stem in (valid_name, 'mpeg4-'+valid_name):
            assert not (producer_data/(stem+'.'+ext)).exists(), 'producer contains valid fixture name'
    preset(datadir/(valid_name+'.ffpreset'),'metadata=comment=ember-default-valid')
    out_default=root/'default.mkv'
    r=subprocess.run([str(exe),'-hide_banner','-loglevel','error','-f','lavfi','-i','color=size=16x16:rate=1','-frames:v','1','-c:v','mpeg4','-vpre',valid_name,str(out_default)],env=env,capture_output=True,text=True)
    if a.expect == 'old':
        assert r.returncode != 0 and 'not found' in r.stderr, r.stderr
    else:
        assert r.returncode == 0, r.stderr
        q=subprocess.run([str(a.prefix/'bin/ffprobe9'),'-v','error','-show_entries','format_tags=COMMENT','-of','default=nw=1',str(out_default)],env=env,capture_output=True,text=True)
        assert q.returncode == 0 and 'ember-default-valid' in q.stdout, q.stderr
    # Valid .avpreset changes the encoder bitrate reported in the output stream.
    preset(datadir/('mpeg4-'+valid_name+'.avpreset'),'b=123456')
    r=invoke('-pre:v',valid_name)
    if a.expect == 'new': assert r.returncode == 0 and '123 kb/s' in r.stderr, r.stderr
    else: assert '123 kb/s' not in r.stderr, r.stderr
    # A valid explicit ffpreset changes observable output container metadata.
    valid=preset(root/'valid.ffpreset','metadata=comment=ember-valid-preset')
    output=root/'valid.mkv'
    e=subprocess.run([str(exe),'-hide_banner','-loglevel','error','-f','lavfi','-i','color=size=16x16:rate=1','-frames:v','1','-c:v','mpeg4','-fpre',str(valid),str(output)],env=env,capture_output=True,text=True)
    assert e.returncode == 0, e.stderr
    probe=subprocess.run([str(a.prefix/'bin/ffprobe9'),'-v','error','-show_entries','format_tags=COMMENT','-of','default=nw=1',str(output)],env=env,capture_output=True,text=True)
    assert probe.returncode == 0 and 'ember-valid-preset' in probe.stdout, probe.stderr
    for name in (token+'.ffpreset','mpeg4-'+token+'.ffpreset','mpeg4-'+token+'.avpreset',token+'.avpreset'):
        (datadir/name).unlink(missing_ok=True)
print('PASS',a.expect)

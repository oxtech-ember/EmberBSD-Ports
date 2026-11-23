#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Run in a desktop PulseAudio session with the installed target Electron."""
import argparse
import array
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

APP = """
const {app, BrowserWindow} = require('electron');
app.whenReady().then(async () => {
  const win = new BrowserWindow({show: false});
  await win.loadURL('data:text/html,<title>Audio output test</title>');
  await win.webContents.executeJavaScript(`
    (async () => {
      const ctx = new AudioContext();
      await ctx.resume();
      const osc = ctx.createOscillator(), gain = ctx.createGain();
      gain.gain.value = 0.08;
      osc.frequency.value = 523;
      osc.connect(gain).connect(ctx.destination);
      osc.start();
      await new Promise(resolve => { osc.onended = resolve; osc.stop(ctx.currentTime + 2); });
      await ctx.close();
    })()`, true);
  app.quit();
}).catch(e => { console.error(e); app.exit(1); });
"""

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--electron', default='/usr/pkg/bin/electron')
    args = parser.parse_args()
    sink = f'electron_probe_{os.getpid()}'
    module = subprocess.check_output(['pactl', 'load-module', 'module-null-sink',
                                      'sink_name=' + sink, 'rate=44100'], text=True).strip()
    try:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / 'main.js'
            script.write_text(APP)
            pcm = root / 'monitor.raw'
            with pcm.open('wb') as output:
                monitor = subprocess.Popen(['parec', '--device='+sink+'.monitor', '--raw',
                    '--format=s16le', '--channels=1', '--rate=44100', '--latency-msec=30'],
                    stdout=output)
                try:
                    subprocess.run([args.electron, '--user-data-dir='+str(root / 'profile'),
                        str(script)], env=dict(os.environ, PULSE_SINK=sink), check=True, timeout=30)
                    time.sleep(0.2)
                    if monitor.poll() is not None:
                        raise RuntimeError('PulseAudio monitor stopped during playback')
                finally:
                    monitor.send_signal(signal.SIGTERM)
                    monitor.wait(timeout=5)
            samples = array.array('h')
            samples.frombytes(pcm.read_bytes())
            if sys.byteorder != 'little':
                samples.byteswap()
            # Measure coherent energy at the generated frequency in 100 ms windows.
            width = 4410
            phase = [2 * math.pi * 523 * i / 44100 for i in range(width)]
            sine, cosine = [math.sin(x) for x in phase], [math.cos(x) for x in phase]
            def amplitude(block):
                return 2 * math.hypot(sum(x*y for x,y in zip(block, sine)),
                                      sum(x*y for x,y in zip(block, cosine))) / width
            active = sum(amplitude(samples[i:i+width]) > 100
                         for i in range(0, len(samples)-width+1, width))
            if active < 8:
                raise SystemExit(f'FAIL: expected 523 Hz on the dedicated PulseAudio output, got {active} windows')
            print(f'PASS: detected 523 Hz in {active} windows on the dedicated output')
    finally:
        subprocess.run(['pactl', 'unload-module', module], check=True)

if __name__ == '__main__':
    main()

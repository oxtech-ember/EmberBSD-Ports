# Browser UI flow diagnostic (draft)

Run in an existing local graphical session as the desktop user. Supply absolute paths to the installed Browser and its matching Electron executable, the exact Electron runtime version and an existing private output directory:

```
python3 browser-flows-run.py --browser /path/to/ember-browser --electron /path/to/electron --electron-version 45.3.2 --output-parent /path/to/results
```

Add `--download-only` for a shorter owned Browser session that tests one download. The fixture and CDP endpoint listen on loopback. The runner creates a fresh private profile and checks normal app exit, its owned process group and exact downloaded bytes. The driver explicitly permits downloads to its isolated directory with CDP `Browser.setDownloadBehavior`; it does not test the native save chooser or default download policy. The download page must expose exactly one matching row in `completed` state. The full mode also checks navigation, private isolation, history and restart. Results and logs remain in a newly created directory under the specified output parent.

The diagnostic sends UI events to its own Browser instance. It does not exercise an existing user profile, physical input, real websites, ad-block policy, notification delivery or physical device reconnection. It does not install or publish anything. CDP is a privileged interface and is limited to the test's loopback instance; run only in a trusted local environment.

## Geolocation permission

Use the same explicit executable and output arguments with
`browser-permissions-run.py`. Its isolated loopback fixture checks the real
geolocation block prompt for the normal and private profiles, normal denial
persistence across a normal restart, and a fresh prompt in a new private tab.
It does not test permission allow, microphone capture, notification delivery,
or location accuracy.

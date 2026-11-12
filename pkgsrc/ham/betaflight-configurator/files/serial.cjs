"use strict";

// Serial grants belong to Electron's WebContents lifetime. Only an explicit
// choice below grants a device; do not install a blanket device permission hook.
const { isAppURL } = require("./app-paths.cjs");

function isAppContents(contents) {
  return contents && !contents.isDestroyed() && isAppURL(contents.getURL());
}

function installSerialSelection(ses, { BrowserWindow, dialog }) {
  const pending = new WeakSet();
  ses.setPermissionRequestHandler((contents, permission, callback, details) => {
    callback(Boolean(isAppContents(contents) &&
      isAppURL(details.requestingUrl) &&
      ["serial", "clipboard-read", "media"].includes(permission)));
  });
  ses.setPermissionCheckHandler((contents, permission, origin) => Boolean(
    isAppContents(contents) && isAppURL(origin) &&
    ["serial", "clipboard-sanitized-write"].includes(permission)));

  ses.on("select-serial-port", (event, ports, contents, callback) => {
    event.preventDefault();
    const parent = contents && BrowserWindow.fromWebContents(contents);
    if (!isAppContents(contents) || !parent || parent.isDestroyed() ||
        pending.has(contents)) {
      callback("");
      return;
    }

    // A native dialog shows a snapshot. A port removed while it is open cannot
    // be selected, even if its identifier is reused by a newly attached device.
    const choices = ports.slice();
    const removed = new Set();
    let finished = false;
    const finish = (portId = "") => {
      if (finished) return;
      finished = true;
      pending.delete(contents);
      ses.removeListener("serial-port-removed", onRemoved);
      contents.removeListener("destroyed", onDestroyed);
      contents.removeListener("did-start-navigation", onNavigation);
      callback(portId);
    };
    const onRemoved = (_event, port, owner) => {
      if (owner === contents) removed.add(port.portId);
    };
    const onDestroyed = () => finish();
    const onNavigation = (details) => {
      if (details.isMainFrame) finish();
    };
    pending.add(contents);
    ses.on("serial-port-removed", onRemoved);
    contents.once("destroyed", onDestroyed);
    contents.on("did-start-navigation", onNavigation);

    const options = {
      type: "question",
      title: "Betaflight Configurator",
      message: "Choose a serial port",
      detail: choices.length ? "Choose the connected flight controller. To refresh the list, cancel and try again."
        : "No matching ports found. Connect the flight controller, then try again.",
      buttons: ["Cancel", ...choices.map((port) =>
        port.displayName ? `${port.displayName} (${port.portName})` : port.portName)],
      defaultId: 0,
      cancelId: 0,
      noLink: true,
    };
    try {
      Promise.resolve(dialog.showMessageBox(parent, options)).then(({ response }) => {
        const selected = Number.isInteger(response) && response > 0 ? choices[response - 1] : null;
        finish(selected && isAppContents(contents) && !removed.has(selected.portId)
          ? selected.portId : "");
      }, () => finish());
    } catch {
      finish();
    }
  });
}

module.exports = { installSerialSelection, isAppURL };

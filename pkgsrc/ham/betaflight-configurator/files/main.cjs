"use strict";

const path = require("path");
const { app, BrowserWindow, protocol, session, shell } = require("electron");

const DIST = path.join(__dirname, "dist");
const SCHEME = "bfapp";

protocol.registerSchemesAsPrivileged([
  {
    scheme: SCHEME,
    privileges: {
      standard: true,
      secure: true,
      supportFetchAPI: true,
      corsEnabled: true,
      stream: true,
    },
  },
]);

function enableSerialPermissions() {
  const ses = session.defaultSession;
  ses.setPermissionRequestHandler((_wc, permission, callback) => {
    callback(permission === "serial" || permission === "clipboard-read" || permission === "media");
  });
  ses.setDevicePermissionHandler((details) => details.deviceType === "serial");
  if (typeof ses.setPermissionCheckHandler === "function") {
    ses.setPermissionCheckHandler((_wc, permission) => permission === "serial" || permission === "clipboard-sanitized-write");
  }
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 1024,
    minHeight: 550,
    title: "Betaflight Configurator",
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      spellcheck: false,
    },
  });
  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });
  win.loadURL(`${SCHEME}://./index.html`);
}

app.whenReady().then(() => {
  protocol.handle(SCHEME, (request) => {
    const { net } = require("electron");
    const url = new URL(request.url);
    let rel = decodeURIComponent(url.pathname || "/");
    if (rel === "/" || rel === "") rel = "/index.html";
    const filePath = path.normalize(path.join(DIST, rel.replace(/^\/+/, "")));
    if (!filePath.startsWith(DIST)) {
      return new Response("Forbidden", { status: 403 });
    }
    return net.fetch("file://" + filePath);
  });
  enableSerialPermissions();
  createWindow();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

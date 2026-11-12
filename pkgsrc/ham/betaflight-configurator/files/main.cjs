"use strict";

const path = require("path");
const { pathToFileURL } = require("node:url");
const { app, BrowserWindow, dialog, protocol, session, shell } = require("electron");
const { installSerialSelection } = require("./serial.cjs");
const { appFilePath, isAllowedExternalURL } = require("./app-paths.cjs");

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
    if (isAllowedExternalURL(url)) shell.openExternal(url);
    return { action: "deny" };
  });
  win.loadURL(`${SCHEME}://./index.html`);
}

app.whenReady().then(() => {
  protocol.handle(SCHEME, (request) => {
    const { net } = require("electron");
    const filePath = appFilePath(DIST, request.url);
    if (filePath === null) {
      return new Response("Forbidden", { status: 403 });
    }
    return net.fetch(pathToFileURL(filePath).href);
  });
  installSerialSelection(session.defaultSession, { BrowserWindow, dialog });
  createWindow();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

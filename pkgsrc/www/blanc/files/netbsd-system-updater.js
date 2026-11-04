'use strict';
// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).
// NetBSD package management owns updates. Never load an upstream app updater.
const { app, BrowserWindow, dialog } = require('electron');

function setupAutoUpdater() {
  console.info('[updater] disabled: system packages own updates');
}

async function checkForUpdatesManually() {
  const options = {
    type: 'info',
    title: app.name,
    message: 'Updates are managed by the system package manager.',
    detail: 'Use the system package manager to check for and install updates.',
  };
  const parent = BrowserWindow.getFocusedWindow();
  if (parent) return dialog.showMessageBox(parent, options);
  return dialog.showMessageBox(options);
}

module.exports = { setupAutoUpdater, checkForUpdatesManually };

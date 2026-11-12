"use strict";

const path = require("node:path");

function isAppURL(value) {
  try {
    const url = new URL(value);
    return url.protocol === "bfapp:" && url.hostname === "." &&
      !url.port && !url.username && !url.password;
  } catch {
    return false;
  }
}

function appFilePath(root, requestURL) {
  if (!isAppURL(requestURL)) return null;
  let name;
  try {
    name = decodeURIComponent(new URL(requestURL).pathname);
  } catch {
    return null;
  }
  if (name.includes("\0")) return null;
  if (name === "" || name === "/") name = "/index.html";
  const file = path.resolve(root, name.replace(/^\/+/, ""));
  const relative = path.relative(root, file);
  return relative === ".." || relative.startsWith(".." + path.sep) ||
    path.isAbsolute(relative) ? null : file;
}

function isAllowedExternalURL(value) {
  try {
    return ["https:", "http:"].includes(new URL(value).protocol);
  } catch {
    return false;
  }
}

module.exports = { appFilePath, isAppURL, isAllowedExternalURL };

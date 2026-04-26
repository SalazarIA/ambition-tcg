const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("AmbitionDesktop", {
    platform: process.platform,
    client: "electron",
    version: "0.1.0"
});

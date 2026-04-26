const { app, BrowserWindow, shell, Menu, nativeImage } = require("electron");
const path = require("path");

const DEFAULT_GAME_URL = "https://ambition-tcg.onrender.com";

const GAME_URL = process.env.AMBITION_DESKTOP_URL || DEFAULT_GAME_URL;

let mainWindow = null;

function createMainMenu() {
    const template = [
        {
            label: "Ambition TCG",
            submenu: [
                {
                    label: "Reload",
                    accelerator: "CmdOrCtrl+R",
                    click: () => {
                        if (mainWindow) {
                            mainWindow.reload();
                        }
                    }
                },
                {
                    label: "Toggle Fullscreen",
                    accelerator: "F11",
                    click: () => {
                        if (mainWindow) {
                            mainWindow.setFullScreen(!mainWindow.isFullScreen());
                        }
                    }
                },
                {
                    type: "separator"
                },
                {
                    label: "Quit",
                    accelerator: "CmdOrCtrl+Q",
                    click: () => {
                        app.quit();
                    }
                }
            ]
        },
        {
            label: "View",
            submenu: [
                {
                    label: "Zoom In",
                    accelerator: "CmdOrCtrl+=",
                    role: "zoomIn"
                },
                {
                    label: "Zoom Out",
                    accelerator: "CmdOrCtrl+-",
                    role: "zoomOut"
                },
                {
                    label: "Reset Zoom",
                    accelerator: "CmdOrCtrl+0",
                    role: "resetZoom"
                },
                {
                    type: "separator"
                },
                {
                    label: "Developer Tools",
                    accelerator: "CmdOrCtrl+Shift+I",
                    click: () => {
                        if (mainWindow) {
                            mainWindow.webContents.toggleDevTools();
                        }
                    }
                }
            ]
        }
    ];

    const menu = Menu.buildFromTemplate(template);
    Menu.setApplicationMenu(menu);
}

function createWindow() {
    const iconPath = path.join(__dirname, "assets", "icon.png");
    const icon = nativeImage.createFromPath(iconPath);

    mainWindow = new BrowserWindow({
        width: 1280,
        height: 800,
        minWidth: 1024,
        minHeight: 680,
        backgroundColor: "#070711",
        title: "Ambition TCG",
        icon: icon.isEmpty() ? undefined : icon,
        show: false,
        autoHideMenuBar: false,
        webPreferences: {
            preload: path.join(__dirname, "preload.cjs"),
            nodeIntegration: false,
            contextIsolation: true,
            sandbox: true,
            webSecurity: true
        }
    });

    mainWindow.once("ready-to-show", () => {
        mainWindow.show();
    });

    mainWindow.webContents.setWindowOpenHandler(({ url }) => {
        if (url.startsWith(GAME_URL)) {
            return { action: "allow" };
        }

        shell.openExternal(url);
        return { action: "deny" };
    });

    mainWindow.webContents.on("will-navigate", (event, url) => {
        const isGameUrl = url.startsWith(GAME_URL);

        if (!isGameUrl) {
            event.preventDefault();
            shell.openExternal(url);
        }
    });

    mainWindow.on("closed", () => {
        mainWindow = null;
    });

    mainWindow.loadURL(GAME_URL);
}

app.whenReady().then(() => {
    createMainMenu();
    createWindow();

    app.on("activate", () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on("window-all-closed", () => {
    if (process.platform !== "darwin") {
        app.quit();
    }
});

const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');
const AdmZip = require('adm-zip');
const { spawn } = require('child_process');

// Component URLs - Latest stable versions
const COMPONENTS = {
    python: {
        name: 'Python Runtime',
        url: 'https://www.python.org/ftp/python/3.14.2/python-3.14.2-embed-amd64.zip',
        dest: 'Runtime/python',
        size: 15 * 1024 * 1024 // ~15 MB compressed
    },
    getPip: {
        name: 'pip Installer',
        url: 'https://bootstrap.pypa.io/get-pip.py',
        dest: 'Runtime/python/get-pip.py',
        isFile: true,
        size: 2 * 1024 * 1024
    },
    electron: {
        name: 'Electron Runtime',
        url: 'https://github.com/electron/electron/releases/download/v39.2.7/electron-v39.2.7-win32-x64.zip',
        dest: 'Runtime/electron',
        size: 136 * 1024 * 1024 // ~136 MB compressed
    },
    git: {
        name: 'MinGit',
        url: 'https://github.com/git-for-windows/git/releases/download/v2.52.0.windows.1/MinGit-2.52.0-64-bit.zip',
        dest: 'Runtime/git',
        size: 42 * 1024 * 1024 // ~42 MB
    },
    launcher: {
        name: 'Flux Launcher',
        url: 'https://github.com/F0RLE/flux-platform/archive/refs/heads/main.zip',
        dest: 'Launcher',
        size: 1 * 1024 * 1024, // ~1 MB
        stripRoot: true // Strip the "flux-platform-main" folder
    }
};

class Installer {
    constructor() {
        this.cancelled = false;
    }

    async install(installPath, onProgress) {
        try {
            // Create base directories
            this.createDirectories(installPath);

            const components = ['python', 'getPip', 'electron', 'git', 'launcher'];
            const totalComponents = components.length;

            for (let i = 0; i < components.length; i++) {
                if (this.cancelled) {
                    return { success: false, error: 'Cancelled' };
                }

                const key = components[i];
                const component = COMPONENTS[key];

                onProgress({
                    step: i + 1,
                    total: totalComponents,
                    name: component.name,
                    status: 'downloading',
                    percent: 0
                });

                const destPath = path.join(installPath, component.dest);

                if (component.isFile) {
                    // Download single file
                    await this.downloadFile(component.url, destPath, (percent) => {
                        onProgress({
                            step: i + 1,
                            total: totalComponents,
                            name: component.name,
                            status: 'downloading',
                            percent
                        });
                    });
                } else {
                    // Download and extract zip
                    const tempZip = path.join(installPath, 'Temp', `${key}.zip`);

                    await this.downloadFile(component.url, tempZip, (percent) => {
                        onProgress({
                            step: i + 1,
                            total: totalComponents,
                            name: component.name,
                            status: 'downloading',
                            percent
                        });
                    });

                    onProgress({
                        step: i + 1,
                        total: totalComponents,
                        name: component.name,
                        status: 'extracting',
                        percent: 100
                    });

                    await this.extractZip(tempZip, destPath, component.stripRoot);

                    // Cleanup temp file
                    try { fs.unlinkSync(tempZip); } catch (e) { }
                }

                onProgress({
                    step: i + 1,
                    total: totalComponents,
                    name: component.name,
                    status: 'done',
                    percent: 100
                });
            }

            // Configure Python
            onProgress({
                step: totalComponents,
                total: totalComponents,
                name: 'Настройка Python',
                status: 'configuring',
                percent: 100
            });

            await this.configurePython(installPath);

            // Install Python dependencies
            onProgress({
                step: totalComponents,
                total: totalComponents,
                name: 'Установка зависимостей',
                status: 'installing',
                percent: 100
            });

            await this.installDependencies(installPath);

            return { success: true };

        } catch (error) {
            console.error('Installation error:', error);
            return { success: false, error: error.message };
        }
    }

    createDirectories(installPath) {
        // Program Files structure
        const dirs = [
            'Runtime/python',
            'Runtime/electron',
            'Runtime/git',
            'Launcher',
            'Logs',
            'Temp'
        ];

        for (const dir of dirs) {
            const fullPath = path.join(installPath, dir);
            fs.mkdirSync(fullPath, { recursive: true });
        }
    }

    downloadFile(url, destPath, onProgress) {
        return new Promise((resolve, reject) => {
            // Ensure dest directory exists
            fs.mkdirSync(path.dirname(destPath), { recursive: true });

            const file = fs.createWriteStream(destPath);

            const makeRequest = (reqUrl) => {
                const protocol = reqUrl.startsWith('https') ? https : http;

                protocol.get(reqUrl, {
                    headers: { 'User-Agent': 'FluxInstaller/1.0' }
                }, (response) => {
                    // Handle redirects
                    if (response.statusCode === 301 || response.statusCode === 302) {
                        file.close();
                        fs.unlinkSync(destPath);
                        makeRequest(response.headers.location);
                        return;
                    }

                    if (response.statusCode !== 200) {
                        reject(new Error(`HTTP ${response.statusCode}`));
                        return;
                    }

                    const totalSize = parseInt(response.headers['content-length'], 10) || 0;
                    let downloaded = 0;

                    response.on('data', (chunk) => {
                        downloaded += chunk.length;
                        if (totalSize > 0) {
                            const percent = Math.round((downloaded / totalSize) * 100);
                            onProgress(percent);
                        }
                    });

                    response.pipe(file);

                    file.on('finish', () => {
                        file.close();
                        resolve();
                    });

                }).on('error', (err) => {
                    fs.unlink(destPath, () => { });
                    reject(err);
                });
            };

            makeRequest(url);
        });
    }

    async extractZip(zipPath, destPath, stripRoot = false) {
        return new Promise((resolve, reject) => {
            try {
                const zip = new AdmZip(zipPath);

                if (stripRoot) {
                    // Extract to temp, then move contents
                    const tempPath = destPath + '_temp';
                    zip.extractAllTo(tempPath, true);

                    // Find the root folder and move its contents
                    const entries = fs.readdirSync(tempPath);
                    if (entries.length === 1) {
                        const rootFolder = path.join(tempPath, entries[0]);
                        const stats = fs.statSync(rootFolder);
                        if (stats.isDirectory()) {
                            // Move contents from root folder to dest
                            fs.mkdirSync(destPath, { recursive: true });
                            const contents = fs.readdirSync(rootFolder);
                            for (const item of contents) {
                                fs.renameSync(
                                    path.join(rootFolder, item),
                                    path.join(destPath, item)
                                );
                            }
                            // Cleanup temp
                            fs.rmSync(tempPath, { recursive: true, force: true });
                            resolve();
                            return;
                        }
                    }

                    // Fallback: just rename temp to dest
                    fs.renameSync(tempPath, destPath);
                } else {
                    zip.extractAllTo(destPath, true);
                }

                resolve();
            } catch (error) {
                reject(error);
            }
        });
    }

    async configurePython(installPath) {
        const pythonDir = path.join(installPath, 'Runtime/python');
        const pthFile = path.join(pythonDir, 'python314._pth');

        // Modify python._pth to enable pip
        if (fs.existsSync(pthFile)) {
            let content = fs.readFileSync(pthFile, 'utf-8');
            // Uncomment import site
            content = content.replace('#import site', 'import site');
            // Add Lib/site-packages
            if (!content.includes('Lib/site-packages')) {
                content += '\nLib/site-packages\n';
            }
            fs.writeFileSync(pthFile, content);
        }

        // Create Lib/site-packages directory
        fs.mkdirSync(path.join(pythonDir, 'Lib/site-packages'), { recursive: true });
    }

    async installDependencies(installPath) {
        const pythonExe = path.join(installPath, 'Runtime/python/python.exe');
        const getPipPath = path.join(installPath, 'Runtime/python/get-pip.py');
        const launcherDir = path.join(installPath, 'Launcher');
        const requirementsPath = path.join(launcherDir, 'requirements.txt');

        // Install pip
        await this.runCommand(pythonExe, [getPipPath, '--no-warn-script-location']);

        // Install requirements if exists
        if (fs.existsSync(requirementsPath)) {
            await this.runCommand(pythonExe, ['-m', 'pip', 'install', '-r', requirementsPath, '--no-warn-script-location']);
        }
    }

    runCommand(command, args) {
        return new Promise((resolve, reject) => {
            const proc = spawn(command, args, {
                windowsHide: true,
                stdio: 'pipe'
            });

            proc.on('close', (code) => {
                if (code === 0) {
                    resolve();
                } else {
                    reject(new Error(`Command failed with code ${code}`));
                }
            });

            proc.on('error', reject);
        });
    }

    async createShortcuts(installPath, desktop = true, startMenu = true) {
        const launchBat = path.join(installPath, 'Launcher/scripts/launch.bat');
        const electronExe = path.join(installPath, 'Runtime/electron/electron.exe');

        // Create a VBS script to create shortcuts (Windows-native)
        const createShortcutVbs = `
Set WshShell = CreateObject("WScript.Shell")

${desktop ? `
Set DesktopShortcut = WshShell.CreateShortcut(WshShell.SpecialFolders("Desktop") & "\\Flux Platform.lnk")
DesktopShortcut.TargetPath = "${launchBat.replace(/\\/g, '\\\\')}"
DesktopShortcut.WorkingDirectory = "${path.join(installPath, 'Launcher').replace(/\\/g, '\\\\')}"
DesktopShortcut.Description = "Flux Platform"
DesktopShortcut.Save
` : ''}

${startMenu ? `
Set StartMenuShortcut = WshShell.CreateShortcut(WshShell.SpecialFolders("StartMenu") & "\\Programs\\Flux Platform.lnk")
StartMenuShortcut.TargetPath = "${launchBat.replace(/\\/g, '\\\\')}"
StartMenuShortcut.WorkingDirectory = "${path.join(installPath, 'Launcher').replace(/\\/g, '\\\\')}"
StartMenuShortcut.Description = "Flux Platform"
StartMenuShortcut.Save
` : ''}
`;

        const vbsPath = path.join(installPath, 'Temp/create_shortcuts.vbs');
        fs.writeFileSync(vbsPath, createShortcutVbs);

        await this.runCommand('cscript', ['//nologo', vbsPath]);

        // Cleanup
        try { fs.unlinkSync(vbsPath); } catch (e) { }

        return { success: true };
    }

    async launchApp(installPath) {
        const launchBat = path.join(installPath, 'Launcher/scripts/launch.bat');

        spawn('cmd.exe', ['/c', launchBat], {
            detached: true,
            stdio: 'ignore',
            cwd: path.join(installPath, 'Launcher')
        }).unref();

        return { success: true };
    }

    cancel() {
        this.cancelled = true;
    }
}

module.exports = { Installer };

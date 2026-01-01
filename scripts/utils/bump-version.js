const fs = require('fs');
const path = require('path');

const packageJsonPath = path.join(__dirname, '../../src/package.json');
const tauriConfPath = path.join(__dirname, '../../src-tauri/tauri.conf.json');

// Read files
const packageJson = require(packageJsonPath);
const tauriConf = require(tauriConfPath);

// Helper to bump patch version
function bumpVersion(version) {
    // If version has a pre-release tag (e.g., 0.0.1-alpha), strip it to go to release (0.0.1)
    if (version.includes('-')) {
        return version.split('-')[0];
    }
    // Otherwise standard patch bump
    const parts = version.split('.').map(Number);
    parts[2] += 1;
    return parts.join('.');
}

const currentVersion = packageJson.version;
const newVersion = bumpVersion(currentVersion);

console.log(`Bumping version: ${currentVersion} -> ${newVersion}`);

// Update package.json
packageJson.version = newVersion;
fs.writeFileSync(packageJsonPath, JSON.stringify(packageJson, null, 2) + '\n');

// Update tauri.conf.json
tauriConf.version = newVersion;
fs.writeFileSync(tauriConfPath, JSON.stringify(tauriConf, null, 4));

// Output new version for GitHub Actions to capture
// We use a special marker or just console.log the raw version if piped
console.log(`::set-output name=new_version::${newVersion}`);

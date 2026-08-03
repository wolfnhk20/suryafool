// src/backend/binary.js
// Python binary manager for CLI wrapper

import { execFileSync, spawn } from 'child_process';
import path from 'path';
import fs from 'fs';
import os from 'os';
import https from 'https';
import { pipeline } from 'stream';
import { promisify } from 'util';
import AdmZip from 'adm-zip';

const __dirname = path.dirname(process.argv[1]);

const pipelineAsync = promisify(pipeline);

export class BinaryManager {
  constructor() {
    this.platform = this.detectPlatform();
    this.binaryPath = this.getBinaryPath();
  }

  detectPlatform() {
    const platform = os.platform();
    const arch = os.arch();
    const map = {
      'win32-x64': 'windows-x64',
      'linux-x64': 'linux-x64',
      'linux-arm64': 'linux-arm64',
      'darwin-x64': 'macos-x64',
      'darwin-arm64': 'macos-arm64',
    };
    return map[`${platform}-${arch}`] || `${platform}-${arch}`;
  }

  getBinaryPath() {
    const binaryName = this.platform.startsWith('windows') ? 'suryafool.exe' : 'suryafool';
    return path.join(__dirname, '..', 'bin', this.platform, binaryName);
  }

  isInstalled() {
    return fs.existsSync(this.binaryPath);
  }

  async fetchBinary(version = 'latest') {
    // Try to use the Python module directly if binary not available
    try {
      execFileSync('python', ['-m', 'bootstrap.agent', '--help'], { stdio: 'ignore' });
      return 'python -m bootstrap.agent';
    } catch {
      // Try to download from GitHub releases
      return await this.downloadBinary(version);
    }
  }

  async downloadBinary(version = 'latest') {
    const url = `https://github.com/your-username/suryafool/releases/download/${version}/suryafool-${this.platform}.zip`;
    const zipPath = path.join(__dirname, '..', 'bin', `${this.platform}.zip`);

    // Ensure bin directory exists
    fs.mkdirSync(path.dirname(zipPath), { recursive: true });

    // Download zip
    await new Promise((resolve, reject) => {
      const file = fs.createWriteStream(zipPath);
      https.get(url, (response) => {
        if (response.statusCode === 302 || response.statusCode === 301) {
          // Follow redirect
          https.get(response.headers.location, (res) => {
            res.pipe(file);
            file.on('finish', () => { file.close(); resolve(); });
          }).on('error', reject);
        } else {
          response.pipe(file);
          file.on('finish', () => { file.close(); resolve(); });
        }
      }).on('error', reject);
    });

    // Extract zip
    const zip = new AdmZip(zipPath);
    zip.extractAllTo(path.dirname(zipPath), true);

    // Cleanup
    fs.unlinkSync(zipPath);

    // Make executable on Unix
    if (!this.platform.startsWith('windows')) {
      fs.chmodSync(this.binaryPath, 0o755);
    }

    return this.binaryPath;
  }

  run(args = [], options = {}) {
    return new Promise((resolve, reject) => {
      // Try Python module first
      const cmd = this.isInstalled() ? this.binaryPath : 'python';
      const argsToUse = this.isInstalled() ? args : ['-m', 'bootstrap.agent', ...args];
      
      const proc = spawn(cmd, argsToUse, {
        stdio: ['pipe', 'pipe', 'pipe'],
        env: { ...process.env, ...options.env },
      });

      let stdout = '';
      let stderr = '';

      proc.stdout.on('data', (data) => {
        const line = data.toString();
        stdout += line;
        if (options.onOutput) options.onOutput(line);
      });

      proc.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      proc.on('close', (code) => {
        if (code === 0) resolve(stdout);
        else reject(new Error(stderr || `Exit code ${code}`));
      });

      proc.on('error', reject);
    });
  }
}

export default BinaryManager;
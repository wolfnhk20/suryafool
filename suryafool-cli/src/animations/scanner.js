// src/animations/scanner.js
// Scanning line animation for scan panels

import chalk from 'chalk';
import { themes } from '../styles/theme.js';

export class Scanner {
  constructor(width = 60, theme = 'cyberpunk') {
    this.width = width;
    this.position = 0;
    this.direction = 1;
    this.theme = themes[theme] || themes.cyberpunk;
    this.active = false;
  }

  start() {
    this.active = true;
    this.animate();
  }

  stop() {
    this.active = false;
  }

  async animate() {
    while (this.active) {
      const line = this.render();
      process.stdout.write('\r' + line);
      await new Promise(r => setTimeout(r, 50));
    }
  }

  render() {
    const before = '─'.repeat(this.position);
    const scanner = '█';
    const after = '─'.repeat(this.width - this.position - 1);
    
    const theme = this.theme;
    const colored = chalk.hex(theme.muted)(before) + 
                    chalk.hex(theme.primary)(scanner) + 
                    chalk.hex(theme.muted)(after);
    
    // Update position
    this.position += this.direction;
    if (this.position >= this.width - 1) this.direction = -1;
    if (this.position <= 0) this.direction = 1;
    
    return colored;
  }
}

export async function scanLine(width = 60, duration = 2000, theme = 'cyberpunk') {
  const scanner = new Scanner(width, theme);
  scanner.start();
  
  await new Promise(r => setTimeout(r, duration));
  
  scanner.stop();
  process.stdout.write('\r' + ' '.repeat(width) + '\r');
}

export { Scanner, scanLine };
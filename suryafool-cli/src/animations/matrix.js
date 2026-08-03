// src/animations/matrix.js
// Matrix rain effect with katakana characters

import gradient from 'gradient-string';
import { themes } from '../styles/theme.js';

const MATRIX_CHARS = 'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ';

export class MatrixRain {
  constructor(columns = 80, theme = 'cyberpunk') {
    this.columns = columns;
    this.drops = Array(columns).fill(1);
    this.theme = themes[theme] || themes.cyberpunk;
  }

  render() {
    const green = gradient(this.theme.success, this.theme.muted);
    let output = '';
    
    for (let i = 0; i < this.columns; i++) {
      const char = MATRIX_CHARS[Math.floor(Math.random() * MATRIX_CHARS.length)];
      const colored = this.drops[i] > 0 ? green(char) : ' ';
      output += colored;
      
      if (this.drops[i] > 0 && Math.random() > 0.975) {
        this.drops[i] = 0;
      }
      this.drops[i]++;
    }
    
    return output;
  }

  static async animate(duration = 5000, columns = null, theme = 'cyberpunk') {
    const width = columns || process.stdout.columns || 80;
    const rain = new MatrixRain(width, theme);
    const startTime = Date.now();
    
    process.stdout.write('\x1b[?25l'); // Hide cursor
    
    try {
      while (Date.now() - startTime < duration) {
        process.stdout.write('\r' + rain.render());
        await new Promise(r => setTimeout(r, 50));
      }
    } finally {
      process.stdout.write('\x1b[?25h'); // Show cursor
    }
  }
}

export default MatrixRain;
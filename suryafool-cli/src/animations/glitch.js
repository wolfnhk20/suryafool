// src/animations/glitch.js
// Glitch text effect for cyberpunk aesthetic

import chalk from 'chalk';
import { themes } from '../styles/theme.js';

async function glitchText(text, options = {}) {
  const { 
    intensity = 3, 
    duration = 500, 
    theme = themes.cyberpunk 
  } = options;
  
  const glitchChars = '!@#$%^&*()_+-=[]{}|;:,.<>?/~`';
  const original = text.split('');
  const iterations = Math.floor(duration / 50);

  for (let i = 0; i < iterations; i++) {
    const glitched = original.map((char, idx) => {
      if (Math.random() < intensity / 10) {
        const replacement = glitchChars[Math.floor(Math.random() * glitchChars.length)];
        return Math.random() > 0.5
          ? chalk.red(replacement)
          : chalk.hex(theme.secondary)(replacement);
      }
      return chalk.hex(theme.primary)(char);
    }).join('');

    process.stdout.write('\r' + glitched);
    await new Promise(r => setTimeout(r, 50));
  }

  process.stdout.write('\r' + chalk.hex(theme.primary)(text));
}

async function glitchLines(lines, options = {}) {
  for (const line of lines) {
    await glitchText(line, options);
    console.log();
    await new Promise(r => setTimeout(r, 100));
  }
}

export { glitchText, glitchLines };
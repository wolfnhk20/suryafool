// src/animations/typewriter.js
// Typewriter effect for text output

import chalk from 'chalk';

export async function typewrite(text, options = {}) {
  const { 
    speed = 30, 
    color = '#00ffff', 
    cursor = '█',
    sound = false 
  } = options;

  process.stdout.write('\x1b[?25l'); // Hide cursor

  for (const char of text) {
    process.stdout.write(chalk.hex(color)(char));
    if (sound) process.stdout.write('\x07'); // Terminal bell
    await new Promise(r => setTimeout(r, speed));
  }

  process.stdout.write('\x1b[?25h'); // Show cursor
  console.log();
}

export async function typewriteLines(lines, options = {}) {
  for (const line of lines) {
    await typewrite(line, options);
  }
}

export async function typewriteWithCursor(text, options = {}) {
  const { speed = 30, color = '#00ffff' } = options;
  
  process.stdout.write('\x1b[?25l');
  
  let displayed = '';
  for (const char of text) {
    displayed += char;
    process.stdout.write('\r' + chalk.hex('#00ffff')(displayed) + ' █');
    await new Promise(r => setTimeout(r, options.speed || 30));
  }
  
  process.stdout.write('\r' + chalk.hex('#00ffff')(text) + ' \n');
  process.stdout.write('\x1b[?25h');
}
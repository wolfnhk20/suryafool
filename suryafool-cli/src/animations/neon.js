// src/animations/neon.js
// Neon pulse/flicker effects

import chalk from 'chalk';
import { themes } from '../styles/theme.js';

export async function neonPulse(text, options = {}) {
  const { 
    duration = 2000, 
    theme = themes.cyberpunk,
    color = theme.primary 
  } = options;
  
  const startTime = Date.now();
  const frames = [
    chalk.hex(color)(text),
    chalk.hex(theme.glow)(text),
    chalk.bold.hex(color)(text),
    chalk.hex(theme.glow)(text),
  ];
  let frameIndex = 0;

  while (Date.now() - startTime < duration) {
    process.stdout.write('\r' + frames[frameIndex % frames.length]);
    frameIndex++;
    await new Promise(r => setTimeout(r, 200));
  }
  
  process.stdout.write('\r' + chalk.hex(color)(text));
}

export async function neonFlicker(text, options = {}) {
  const { 
    duration = 1500, 
    theme = themes.cyberpunk,
    baseColor = theme.primary,
    flickerColor = theme.glow 
  } = options;
  
  const startTime = Date.now();
  
  while (Date.now() - startTime < duration) {
    const flicker = Math.random() > 0.7;
    const output = flicker 
      ? chalk.bold.hex(flickerColor)(text)
      : chalk.hex(baseColor)(text);
    
    process.stdout.write('\r' + output);
    await new Promise(r => setTimeout(r, 50 + Math.random() * 100));
  }
  
  process.stdout.write('\r' + chalk.hex(baseColor)(text));
}
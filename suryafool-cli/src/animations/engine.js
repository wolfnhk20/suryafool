// src/animations/engine.js
// Core animation engine for CLI effects

import chalk from 'chalk';

export class AnimationEngine {
  constructor(options = {}) {
    this.frameRate = options.frameRate || 30;
    this.running = false;
    this.layers = [];
    this.frameCallback = null;
  }

  addLayer(layer) {
    if (layer && typeof layer.render === 'function') {
      this.layers.push(layer);
    }
    return this;
  }

  removeLayer(layer) {
    this.layers = this.layers.filter(l => l !== layer);
    return this;
  }

  async start() {
    this.running = true;
    while (this.running) {
      const frame = this.layers
        .filter(l => l.active !== false)
        .map(l => l.render())
        .join('\n');
      
      process.stdout.write('\x1b[H' + frame);
      await this.sleep(1000 / this.frameRate);
    }
  }

  stop() {
    this.running = false;
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async fadeIn(content, duration = 1000) {
    const steps = 20;
    for (let i = 0; i <= steps; i++) {
      const opacity = i / steps;
      process.stdout.write('\x1b[H' + content + `\n\x1b[38;2;${Math.floor(255*opacity)};${Math.floor(255*opacity)};${Math.floor(255*opacity)}m`);
      await this.sleep(duration / steps);
    }
  }

  async fadeOut(content, duration = 1000) {
    const steps = 20;
    for (let i = steps; i >= 0; i--) {
      const opacity = i / steps;
      process.stdout.write('\x1b[H' + content + `\n\x1b[38;2;${Math.floor(255*opacity)};${Math.floor(255*opacity)};${Math.floor(255*opacity)}m`);
      await this.sleep(duration / steps);
    }
  }

  async slideIn(content, direction = 'left', duration = 500) {
    const cols = process.stdout.columns || 80;
    const steps = 20;
    const lines = content.split('\n');
    
    for (let i = 0; i <= steps; i++) {
      const progress = i / steps;
      let output = '';
      
      if (direction === 'left') {
        const padding = Math.floor((1 - progress) * cols / 2);
        output = lines.map(l => ' '.repeat(padding) + l).join('\n');
      } else if (direction === 'right') {
        const padding = Math.floor((1 - progress) * cols / 2);
        output = lines.map(l => ' '.repeat(cols - l.length - padding) + l).join('\n');
      } else {
        output = content;
      }
      
      process.stdout.write('\x1b[H' + output);
      await this.sleep(duration / steps);
    }
  }

  async typewrite(text, speed = 30, colorFn = null) {
    process.stdout.write('\x1b[?25l'); // Hide cursor
    
    for (const char of text) {
      const output = colorFn ? colorFn(char) : char;
      process.stdout.write(output);
      await this.sleep(speed);
    }
    
    process.stdout.write('\x1b[?25h'); // Show cursor
  }

  async glitch(text, intensity = 3, duration = 500) {
    const glitchChars = '!@#$%^&*()_+-=[]{}|;:,.<>?/~`';
    const original = text.split('');
    const iterations = Math.floor(duration / 50);

    for (let i = 0; i < iterations; i++) {
      const glitched = original.map((char, idx) => {
        if (Math.random() < intensity / 10) {
          const replacement = glitchChars[Math.floor(Math.random() * glitchChars.length)];
          return Math.random() > 0.5
            ? chalk.red(replacement)
            : chalk.magenta(replacement);
        }
        return char;
      }).join('');

      process.stdout.write('\r' + glitched);
      await this.sleep(50);
    }

    process.stdout.write('\r' + chalk.cyan(text));
  }
}

export default AnimationEngine;
// src/components/BootSequence.js
// Animated boot sequence with matrix rain, glitch, typewriter

import React from 'react';
import { Text, Box } from 'ink';
import chalk from 'chalk';
import MatrixRain from '../animations/matrix.js';
import { typewriteLines, typewriteWithCursor } from '../animations/typewriter.js';
import { glitchText } from '../animations/glitch.js';
import { neonPulse } from '../animations/neon.js';
import { themes } from '../styles/theme.js';

const ASCII_LOGO = `
███████╗██╗   ██╗██╗   ██╗███████╗██╗      ██████╗ ██╗    ██╗
██╔════╝██║   ██║██║   ██║██╔════╝██║     ██╔═══██╗██║    ██║
███████╗██║   ██║██║   ██║███████╗██║     ██║   ██║██║ █╗ ██║
╚════██║██║   ██║██║   ██║╚════██║██║     ██║   ██║██║███╗██║
███████║╚██████╔╝╚██████╔╝███████╗███████╗╚██████╔╝╚███╔███╔╝
╚══════╝ ╚═════╝  ╚═════╝ ╚══════╝╚══════╝ ╚═════╝  ╚══╝╚══╝
`;

export async function bootSequence(onComplete, options = {}) {
  const theme = themes.cyberpunk;
  const { skipAnimations = false } = options;

  if (skipAnimations) {
    console.log('\x1b[2J\x1b[H'); // Clear screen
    console.log(chalk.hex(theme.primary)(ASCII_LOGO));
    console.log(chalk.hex(theme.muted)('Universal Agentic Wireless Platform'));
    console.log(chalk.hex(theme.muted)('v0.1.0'));
    console.log(chalk.hex(theme.muted)('─'.repeat(60)));
    if (onComplete) onComplete();
    return;
  }

  // Phase 1: Matrix rain (2 seconds)
  await MatrixRain.animate(2000);

  // Phase 2: Glitch logo
  process.stdout.write('\x1b[2J\x1b[H'); // Clear screen
  await glitchText(ASCII_LOGO, { intensity: 5, duration: 1000 });

  // Phase 3: Tagline typewrite
  console.log();
  await typewriteLines([
    '>> INITIALIZING WIRELESS AWARENESS PLATFORM...',
  ], {
    speed: 20,
    color: theme.success
  });

  // Phase 4: System checks with animated dots
  const checks = [
    'Loading capability registry...',
    'Initializing hardware abstraction layer...',
    'Connecting to LLM providers...',
    'Activating scope guardian...',
    'Loading mission agents...',
    'System ready.'
  ];

  for (const check of checks) {
    await typewrite(`  [✓] ${check}`, {
      speed: 15,
      color: theme.muted
    });
    await new Promise(r => setTimeout(r, 200));
  }

  // Phase 5: Final flash
  console.log();
  await glitchText('  SURYAFOOL v0.1.0 — READY', {
    intensity: 2,
    duration: 300
  });

  console.log(chalk.hex(theme.muted)('  ' + '─'.repeat(40)));

  if (onComplete) onComplete();
}

export { ASCII_LOGO };
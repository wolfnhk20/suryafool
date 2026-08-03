#!/usr/bin/env node

// scripts/fetch-binary.cjs
// Post-install script to download the correct platform binary

import chalk from 'chalk';
import { BinaryManager } from '../src/backend/binary.js';

const spinnerFrames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'];

function startSpinner(text) {
  let i = 0;
  const interval = setInterval(() => {
    process.stdout.write(`\r${chalk.cyan(spinnerFrames[i % spinnerFrames.length])} ${text}`);
    i++;
  }, 80);
  return interval;
}

function stopSpinner(interval, successText) {
  clearInterval(interval);
  process.stdout.write('\r' + ' '.repeat(60) + '\r');
  console.log(successText);
}

async function postinstall() {
  const binary = new BinaryManager();

  if (binary.isInstalled()) {
    console.log(chalk.green('✓ Suryafool binary already installed.'));
    return;
  }

  const interval = startSpinner(`Downloading suryafool for ${binary.platform}...`);

  try {
    await binary.fetchBinary();
    stopSpinner(interval, chalk.green(`✓ Suryafool installed for ${binary.platform}`));
  } catch (err) {
    stopSpinner(interval, chalk.red('✗ Failed to download binary'));
    console.error(chalk.red(err.message));
    console.log(chalk.yellow('\nFallback: Install Python dependencies manually:'));
    console.log(chalk.cyan('  pip install -r requirements.txt'));
    process.exit(1);
  }
}

postinstall();
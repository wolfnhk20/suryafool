#!/usr/bin/env node

import { render } from 'ink';
import React from 'react';

// Anchor cwd at the repo root so the relative `../dist/index.mjs` import
// resolves regardless of where the user invoked the CLI from. Set by
// bin/suryafool.js via the SURYAFOOL_REPO_ROOT env var.
if (process.env.SURYAFOOL_REPO_ROOT && process.env.SURYAFOOL_REPO_ROOT !== process.cwd()) {
  try {
    process.chdir(process.env.SURYAFOOL_REPO_ROOT);
  } catch (err) {
    console.error('Failed to chdir to SURYAFOOL_REPO_ROOT:', err.message);
  }
}

import App from '../dist/index.mjs';

const argv = JSON.parse(process.env.SURYAFOOL_ARGS || '{}');
const theme = argv.clean ? 'clean' : 'cyberpunk';

// Only use fake TTY if stdin is NOT a real TTY (e.g., when piped or in non-interactive env)
const isRealTTY = process.stdin.isTTY === true;

let stdinForInk = process.stdin;
if (!isRealTTY) {
  // Create a stdin stream that pretends to be a TTY for non-TTY environments
  stdinForInk = new Proxy(process.stdin, {
    get(target, prop, receiver) {
      if (prop === 'isTTY') return true;
      if (prop === 'setRawMode') return () => {};
      if (prop === 'ref' || prop === 'unref') return () => {};
      if (typeof target[prop] === 'function') return target[prop].bind(target);
      return Reflect.get(target, prop, receiver);
    }
  });
}

try {
  const initialState = {
    activeTab: 'dashboard',
    dashboard: { findings: [], progress: 0 },
    agents: [],
    modal: null,
    theme: 'cyberpunk',
    logs: [],
    commandHistory: [],
    currentCommand: null,
    commandStatus: 'idle',
  };
  if (argv._helpOverlay || process.env.SURYAFOOL_HELP_OVERLAY === '1') {
    initialState.modal = { type: 'help', title: 'Help', message: '' };
  }

  const { waitUntilExit } = render(
    React.createElement(App, {
      command: argv._?.[0] || null,
      args: argv._?.slice(1) || [],
      flags: argv,
      theme,
      initialState,
    }),
    {
      stdin: stdinForInk,
      exitOnCtrlC: true,
      patchConsole: false,
    }
  );

  await waitUntilExit;
} catch (err) {
  console.error('Suryafool UI failed to start:', err.message);
  console.error(err.stack);
  process.exit(1);
}
#!/usr/bin/env node

import { render } from 'ink';
import React from 'react';
import App from '../dist/index.mjs';

const argv = JSON.parse(process.env.SURYAFOOL_ARGS || '{}');
const theme = argv.clean ? 'clean' : 'cyberpunk';

// Create a stdin stream that pretends to be a TTY and supports raw mode (by mocking)
const originalStdin = process.stdin;
const ttyStdin = new Proxy(originalStdin, {
  get(target, prop, receiver) {
    if (prop === 'isTTY') {
      return true;
    }
    if (prop === 'setRawMode') {
      // Return a no-op function to avoid errors when Ink tries to set raw mode
      return () => {};
    }
    if (prop === 'ref' || prop === 'unref') {
      // Return a no-op function for ref/unref
      return () => {};
    }
    // For function properties, bind them to the original stdin to ensure correct 'this'
    if (typeof target[prop] === 'function') {
      return target[prop].bind(target);
    }
    // For all other properties, return the value from the original stdin
    return Reflect.get(target, prop, receiver);
  }
});

const { waitUntilExit } = render(
  React.createElement(App.default || App, {
    command: argv._?.[0] || null,
    args: argv._?.slice(1) || [],
    flags: argv,
    theme,
  }),
  {
    stdin: ttyStdin,
    interactive: false
  }
);

await waitUntilExit;
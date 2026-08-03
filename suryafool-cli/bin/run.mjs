#!/usr/bin/env node

import { render } from 'ink';
import React from 'react';
import App from '../dist/index.mjs';

const argv = JSON.parse(process.env.SURYAFOOL_ARGS || '{}');
const theme = argv.clean ? 'clean' : 'cyberpunk';

const { waitUntilExit } = render(
  React.createElement(App.default || App, {
    command: argv._?.[0] || null,
    args: argv._?.slice(1) || [],
    flags: argv,
    theme,
  })
);

await waitUntilExit;
// src/app.test.js
import { test } from 'node:test';
import { render } from 'ink-testing-library';
import assert from 'node:assert';
import React from 'react';
import App from './app.js';

test('renders without throwing', async () => {
  const { unmount } = render(React.createElement(App, { command: null, args: [], flags: {}, theme: 'cyberpunk' }));
  // Wait a bit for any async effects? Not needed for this test.
  assert.ok(true, 'Component rendered');
  unmount();
});
// src/components/CommandBar.js
import React from 'react';
import { Box, Text } from 'ink';
import InputPrompt from './InputPrompt.js';

function CommandBar({ theme = 'cyberpunk', onCommand }) {
  const themes = {
    cyberpunk: { primary: '#00ffff', muted: '#444466', border: '#1a1a3a', background: '#0a0a1a' },
    clean: { primary: '#4a9eff', muted: '#7f8c8d', border: '#3a3a5a', background: '#1e1e2e' },
  };
  const t = themes[theme] || themes.cyberpunk;

  return (
    <Box padding={1} backgroundColor={t.background}>
      <InputPrompt onSubmit={onCommand} theme={theme} placeholder="Enter command..." />
    </Box>
  );
}

export default CommandBar;
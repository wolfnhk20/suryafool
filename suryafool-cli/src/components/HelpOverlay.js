// src/components/HelpOverlay.js
import React from 'react';
import { Box, Text } from 'ink';

function HelpOverlay({ theme = 'cyberpunk' }) {
  const themes = {
    cyberpunk: { primary: '#00ffff', text: '#e0e0ff', muted: '#444466', border: '#1a1a3a', background: '#0a0a1a' },
    clean: { primary: '#4a9eff', text: '#d0d0e0', muted: '#7f8c8d', border: '#3a3a5a', background: '#1e1e2e' },
  };
  const t = themes[theme] || themes.cyberpunk;

  return (
    <Box
      position="absolute"
      top={0}
      left={0}
      right={0}
      bottom={0}
      flexDirection="column"
      padding={2}
      backgroundColor={t.background}
    >
      <Text color={t.primary} bold marginBottom={1}>HELP</Text>
      <Text color={t.text}>Tab navigation: [Tab] / [Shift+Tab]</Text>
      <Text color={t.text}>Commands: scan, audit, explore, agents, config, doctor, clear, help, exit</Text>
      <Text color={t.text}>Press [Esc] or [?] to close</Text>
    </Box>
  );
}

export default HelpOverlay;
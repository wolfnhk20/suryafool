// src/components/Header.js
import React from 'react';
import { Box, Text } from 'ink';

function Header({ theme = 'cyberpunk' }) {
  const themes = {
    cyberpunk: { primary: '#00ffff', text: '#e0e0ff', border: '#1a1a3a' },
    clean: { primary: '#4a9eff', text: '#d0d0e0', border: '#3a3a5a' },
  };
  const t = themes[theme] || themes.cyberpunk;

  return (
    <Box paddingX={1} height={3}>
      <Text color={t.primary} bold>��⚡ SURYAFOOL</Text>
      <Text color={t.muted}>Universal Agentic Wireless Platform</Text>
    </Box>
  );
}

export default Header;
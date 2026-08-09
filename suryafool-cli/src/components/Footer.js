// src/components/Footer.js
import React from 'react';
import { Box, Text } from 'ink';

function Footer({ theme = 'cyberpunk' }) {
  const themes = {
    cyberpunk: { primary: '#00ffff', muted: '#444466', border: '#1a1a3a' },
    clean: { primary: '#4a9eff', muted: '#7f8c8d', border: '#3a3a5a' },
  };
  const t = themes[theme] || themes.cyberpunk;

  return (
    <Box paddingX={1} height={2}>
      <Text color={t.muted}>[Tab] Switch | [Ctrl+C] Quit | [?] Help</Text>
    </Box>
  );
}

export default Footer;
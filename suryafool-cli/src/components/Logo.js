// src/components/Logo.js
// Suryafool logo component with ASCII art

import React from 'react';
import { Text, Box } from 'ink';
import { themes } from '../styles/theme.js';

const ASCII_LOGO = `
███████╗██╗   ██╗██╗   ██╗███████╗██╗      ██████╗ ██╗    ██╗
██╔════╝██║   ██║██║   ██║██╔════╝██║     ██╔═══██╗██║    ██║
███████╗██║   ██║██║   ██║███████╗██║     ██║   ██║██║ █╗ ██║
╚════██║██║   ██║██║   ██║╚════██║██║     ██║   ██║██║███╗██║
███████║╚██████╔╝╚██████╔╝███████╗███████╗╚██████╔╝╚███╔███╔╝
╚══════╝ ╚═════╝  ╚═════╝ ╚══════╝╚══════╝ ╚═════╝  ╚══╝╚══╝
`;

function Logo({ compact = false, theme = 'cyberpunk' }) {
  const t = themes[theme] || themes.cyberpunk;
  
  if (compact) {
    return (
      <Box flexDirection="column" marginBottom={1}>
        <Text bold color={t.primary}>⚡ SURYAFOOL</Text>
        <Text color={t.muted}>v0.1.0</Text>
      </Box>
    );
  }

  return (
    <Box flexDirection="column" borderStyle="single" borderColor={t.border} padding={1} marginBottom={1}>
      <Text bold color={t.primary}>{ASCII_LOGO}</Text>
      <Text color={t.muted}>Universal Agentic Wireless Platform</Text>
      <Text color={t.muted}>v0.1.0</Text>
    </Box>
  );
}

export default Logo;
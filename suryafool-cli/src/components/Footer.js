// src/components/Footer.js
import React from 'react';
import { Box, Text } from 'ink';
import { themes } from '../styles/theme.js';

function Footer({ theme = 'cyberpunk' }) {
  const t = themes[theme] || themes.cyberpunk;

  const KeyHint = ({ k, label }) => (
    <>
      <Text color={t.textDim}>  </Text>
      <Text color={t.primary}>{k}</Text>
      <Text color={t.textDim}> {label}</Text>
    </>
  );

  const Separator = () => (
    <Text color={t.border}>  ·  </Text>
  );

  return (
    <Box
      flexDirection="row"
      justifyContent="space-between"
      alignItems="center"
      paddingX={2}
      height={3}
      borderStyle="single"
      borderColor={t.border}
    >
      <Box flexDirection="row">
        <KeyHint k="Tab" label="switch" />
        <Separator />
        <KeyHint k="?" label="help" />
        <Separator />
        <KeyHint k="Ctrl+L" label="clear log" />
      </Box>
      <Box flexDirection="row">
        <KeyHint k="Ctrl+C" label="quit" />
      </Box>
    </Box>
  );
}

export default Footer;
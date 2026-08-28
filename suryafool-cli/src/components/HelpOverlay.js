// src/components/HelpOverlay.js
import React from 'react';
import { Box, Text } from 'ink';
import Glyph from './Glyph.js';
import { themes } from '../styles/theme.js';

function HelpOverlay({ theme = 'cyberpunk' }) {
  const t = themes[theme] || themes.cyberpunk;

  const Section = ({ title, children }) => (
    <Box flexDirection="column" marginBottom={1}>
      <Text color={t.primary} bold>{title}</Text>
      <Box flexDirection="column" marginLeft={2} marginTop={0}>
        {children}
      </Box>
    </Box>
  );

  const Row = ({ label, value }) => (
    <Box flexDirection="row">
      <Text color={t.textDim}>  {label.padEnd(14, ' ')}</Text>
      <Text color={t.text}>{value}</Text>
    </Box>
  );

  return (
    <Box
      position="absolute"
      top="10%"
      left="10%"
      width="80%"
      height="80%"
      flexDirection="column"
      paddingX={3}
      paddingY={1}
      borderStyle="single"
      borderColor={t.primary}
      backgroundColor={t.background}
    >
      <Box marginBottom={1} flexDirection="row" alignItems="center">
        <Glyph color={t.primary} />
        <Text color={t.primary} bold>  SURYAFOOL REFERENCE</Text>
      </Box>
      <Box flexDirection="row">
        <Box flexDirection="column" flexBasis="50%" paddingRight={2}>
          <Section title="MISSIONS">
            <Row label="scan" value="Scan a target for signals" />
            <Row label="audit" value="Audit a device" />
            <Row label="explore" value="Discover all devices" />
            <Row label="agents" value="List mission agents" />
            <Row label="doctor" value="Verify environment" />
            <Row label="capabilities" value="List available capabilities (P2)" />
            <Row label="scenarios" value="List simulator scenarios (P2)" />
            <Row label="providers" value="List backends (P2.5)" />
            <Row label="run" value="Execute a run (P2/P2.5)" />
            <Row label="show/report" value="Inspect a run (P2)" />
            <Row label="help" value="Show this overlay" />
          </Section>
          <Section title="CONCEPTS">
            <Row label="Environment" value="Local wireless context" />
            <Row label="Mission" value="An active task" />
            <Row label="Discovery" value="Finding new devices" />
            <Row label="Verification" value="Confirming findings" />
          </Section>
        </Box>
        <Box flexDirection="column" flexBasis="50%">
          <Section title="KEYBOARD">
            <Row label="Tab" value="Switch panels" />
            <Row label="?" value="Toggle this overlay" />
            <Row label="Ctrl+L" value="Clear mission log" />
            <Row label="Ctrl+C" value="Quit" />
          </Section>
          <Section title="VIEWS">
            <Row label="Overview" value="Environment snapshot" />
            <Row label="Agents" value="Active mission agents" />
            <Row label="Findings" value="Discovery results" />
            <Row label="Config" value="Runtime state" />
          </Section>
        </Box>
      </Box>
      <Box marginTop={1}>
        <Text color={t.textDim}>Press </Text>
        <Text color={t.primary}>?</Text>
        <Text color={t.textDim}> to close this overlay.</Text>
      </Box>
    </Box>
  );
}

export default HelpOverlay;
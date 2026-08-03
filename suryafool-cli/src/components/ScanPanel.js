// src/components/ScanPanel.js
// Live scan results display

import React, { useState, useEffect } from 'react';
import { Text, Box } from 'ink';
import chalk from 'chalk';
import { themes } from '../styles/theme.js';

function ScanPanel({ 
  target, 
  findings = [], 
  phase = 'scanning', 
  progress = 0, 
  theme = 'cyberpunk' 
}) {
  const t = themes[theme] || themes.cyberpunk;
  const [localProgress, setLocalProgress] = useState(progress);

  useEffect(() => {
    setLocalProgress(progress);
  }, [progress]);

  useEffect(() => {
    if (phase === 'scanning' || phase === 'auditing') {
      const interval = setInterval(() => {
        setLocalProgress(p => Math.min(p + Math.random() * 3, 95));
      }, 300);
      return () => clearInterval(interval);
    }
  }, [phase]);

  const filled = Math.floor((localProgress / 100) * 20);
  const empty = 20 - filled;
  const bar = '█'.repeat(filled) + '░'.repeat(empty);

  return (
    <Box
      flexDirection="column"
      borderStyle="double"
      borderColor={t.primary}
      padding={1}
      width="100%"
    >
      {/* Header */}
      <Box justifyContent="space-between" marginBottom={1}>
        <Text color={t.primary} bold>⚡ SCANNING: {target}</Text>
        <Text color={t.success}>{Math.floor(localProgress)}%</Text>
      </Box>

      {/* Progress bar */}
      <Box marginBottom={1}>
        <Text color={t.muted}>Progress: </Text>
        <Text color={localProgress >= 80 ? t.success : t.primary}>{'█'.repeat(Math.floor(localProgress / 5))}{'░'.repeat(20 - Math.floor(localProgress / 5))}</Text>
        <Text color={t.accent}> {Math.floor(localProgress)}%</Text>
      </Box>

      {/* Findings */}
      {findings.length > 0 && (
        <Box flexDirection="column" marginTop={1}>
          <Text color={t.secondary} bold>FINDINGS:</Text>
          {findings.map((f, i) => (
            <Box key={i} paddingLeft={2}>
              <Text color={f.severity === 'critical' ? t.error : f.severity === 'high' ? t.highlight : t.accent}>
                [{f.severity.toUpperCase()}]
              </Text>
              <Text color={t.text}> {f.description || f.type}</Text>
              {f.signal && <Text color={t.muted}> (Signal: {f.signal})</Text>}
              {f.risk && <Text color={f.risk === 'high' ? t.error : t.muted}> Risk: {f.risk}</Text>}
            </Box>
          ))}
        </Box>
      )}

      {/* Agent status */}
      <Box marginTop={1} borderStyle="single" borderColor={t.border} padding={1}>
        <Text color={t.muted}>Agent: </Text>
        <Text color={t.success}>Signal Intelligence</Text>
        <Text color={t.muted}> | Phase: </Text>
        <Text color={t.accent}>{phase}</Text>
      </Box>
    </Box>
  );
}

export default ScanPanel;
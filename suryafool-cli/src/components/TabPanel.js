// src/components/TabPanel.js
import React from 'react';
import { Box, Text } from 'ink';
import { useState } from '../state/context.js';

function TabPanel({ theme = 'cyberpunk' }) {
  const themes = {
    cyberpunk: { primary: '#00ffff', text: '#e0e0ff', muted: '#444466', border: '#1a1a3a', background: '#0a0a1a' },
    clean: { primary: '#4a9eff', text: '#d0d0e0', muted: '#7f8c8d', border: '#3a3a5a', background: '#1e1e2e' },
  };
  const t = themes[theme] || themes.cyberpunk;
  const state = useState();

  const tabs = ['dashboard', 'agents', 'findings'];
  const activeTab = state.activeTab || 'dashboard';

  return (
    <Box flexGrow={1} flexDirection="column" padding={1}>
      <Box flexDirection="row" marginBottom={1}>
        {tabs.map(tab => (
          <Box
            key={tab}
            marginRight={1}
            paddingX={2}
            backgroundColor={activeTab === tab ? t.background : 'transparent'}
          >
            <Text color={activeTab === tab ? t.primary : t.muted} bold={activeTab === tab}>
              {tab.toUpperCase()}
            </Text>
          </Box>
        ))}
      </Box>
      <Box flexGrow={1} padding={1}>
        <Text color={t.text}>Tab: {activeTab}</Text>
        {activeTab === 'dashboard' && (
          <Box flexDirection="column" marginTop={1}>
            <Text color={t.primary} bold>FINDINGS:</Text>
            {state.dashboard?.findings?.length > 0 ? (
              state.dashboard.findings.map((f, i) => (
                <Text key={i} color={t.success}>  � ✓ {f}</Text>
              ))
            ) : (
              <Text color={t.muted}>  No findings yet</Text>
            )}
            <Text color={t.primary} bold marginTop={1}>PROGRESS: {state.dashboard?.progress || 0}%</Text>
          </Box>
        )}
        {activeTab === 'agents' && (
          <Box flexDirection="column" marginTop={1}>
            <Text color={t.primary} bold>ACTIVE AGENTS:</Text>
            {state.agents?.length > 0 ? (
              state.agents.map((a, i) => (
                <Text key={i} color={t.accent}>  � ► {a}</Text>
              ))
            ) : (
              <Text color={t.muted}>  No active agents</Text>
            )}
          </Box>
        )}
        {activeTab === 'findings' && (
          <Box flexDirection="column" marginTop={1}>
            <Text color={t.primary} bold>ALL FINDINGS:</Text>
            {state.dashboard?.findings?.length > 0 ? (
              state.dashboard.findings.map((f, i) => (
                <Text key={i} color={t.text}>  {i + 1}. {f}</Text>
              ))
            ) : (
              <Text color={t.muted}>  No findings recorded</Text>
            )}
          </Box>
        )}
      </Box>
    </Box>
  );
}

export default TabPanel;
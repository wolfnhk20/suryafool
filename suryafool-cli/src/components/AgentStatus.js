// src/components/AgentStatus.js
// Agent status tracker

import React from 'react';
import { Text, Box } from 'ink';
import chalk from 'chalk';
import { themes } from '../styles/theme.js';

const AGENTS = [
  { name: 'Orchestrator', icon: '🎯', default: true },
  { name: 'Discovery', icon: '🔍' },
  { name: 'Signal Intel', icon: '📡' },
  { name: 'Device Intel', icon: '📱' },
  { name: 'Correlation', icon: '🔗' },
  { name: 'Experiment', icon: '🧪' },
  { name: 'Security Research', icon: '🔓' },
  { name: 'Attack Planning', icon: '⚔️' },
  { name: 'Verification', icon: '✅' },
  { name: 'Skeptic', icon: '🤔' },
  { name: 'Memory', icon: '🧠' },
];

function AgentStatus({ activeAgents = [], theme = 'cyberpunk' }) {
  const t = themes[theme] || themes.cyberpunk;

  return (
    <Box flexDirection="column" borderStyle="single" borderColor={t.border} padding={1}>
      <Text color={t.primary} bold>⚡ AGENT STATUS</Text>
      <Box marginTop={1} flexDirection="column">
        {AGENTS.map((agent, i) => {
          const isActive = activeAgents.includes(agent.name) || (agent.default && activeAgents.length === 0);
          const statusColor = isActive ? t.success : t.muted;
          const statusText = isActive ? 'ACTIVE' : 'IDLE';
          const icon = agent.icon;
          
          return (
            <Box key={i} justifyContent="space-between" width="100%">
              <Text>
                <Text color={t.secondary}>{icon}</Text>
                <Text color={t.text}> {agent.name}</Text>
              </Text>
              <Text color={isActive ? t.success : t.muted}>[{isActive ? 'ACTIVE' : 'IDLE'}]</Text>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
}

export default AgentStatus;
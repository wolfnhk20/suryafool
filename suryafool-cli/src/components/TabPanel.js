// src/components/TabPanel.js
import React from 'react';
import { Box, Text } from 'ink';
import { useState, useDispatch } from '../state/context.js';
import { themes } from '../styles/theme.js';
import ScanDashboard from './ScanDashboard.js';
import AgentsBoard from './AgentsBoard.js';
import ConfigView from './ConfigView.js';
import CapabilitiesView from './CapabilitiesView.js';
import EvidenceFeed from './EvidenceFeed.js';

function TabPanel({ theme = 'cyberpunk' }) {
  const t = themes[theme] || themes.cyberpunk;
  const state = useState();
  const dispatch = useDispatch();

  const tabs = [
    { id: 'dashboard',    label: 'Main' },
    { id: 'agents',       label: 'Agents' },
    { id: 'evidence',     label: 'Evidence' },
    { id: 'findings',     label: 'Findings' },
    { id: 'capabilities', label: 'Caps' },
    { id: 'config',       label: 'Config' },
  ];

  const activeTab = state.activeTab || 'dashboard';

  const handleTabClick = (tabId) => {
    dispatch({ type: 'SET_TAB', payload: tabId });
  };

  const renderFindings = () => (
    <Box flexDirection="column" paddingX={1}>
      <Text color={t.textDim} dimColor>FINDINGS</Text>
      <Box marginTop={1} flexDirection="column">
        {state.dashboard?.findings && state.dashboard.findings.length > 0 ? (
          state.dashboard.findings.map((finding, i) => (
            <Box key={i} flexDirection="row" marginBottom={0}>
              <Text color={t.accent}>{'  '}{String(i + 1).padStart(3, '0')}{' '}</Text>
              <Text color={t.text}>{typeof finding === 'string' ? finding : JSON.stringify(finding)}</Text>
            </Box>
          ))
        ) : (
          <>
            <Text color={t.muted}>  No findings recorded</Text>
            <Text color={t.textDim}>  </Text>
            <Text color={t.textDim}>  Findings appear here after running discovery.</Text>
          </>
        )}
      </Box>
    </Box>
  );

  return (
    <Box flexDirection="column" flexGrow={1}>
      <Box flexDirection="row" paddingX={1} height={3} alignItems="center">
        <Text>
          {tabs.map((tab, idx) => {
            const isActive = activeTab === tab.id;
            const color = isActive ? t.primary : t.textDim;
            const bold = isActive;
            return (
              <React.Fragment key={tab.id}>
                {idx > 0 && <Text color={t.border}>{'  '}</Text>}
                <Text color={color} bold={bold}>{tab.label}</Text>
              </React.Fragment>
            );
          })}
        </Text>
      </Box>
      <Box flexDirection="column" flexGrow={1} paddingY={1} borderStyle="single" borderColor={t.border}>
        {activeTab === 'dashboard' && <ScanDashboard theme={theme} />}
        {activeTab === 'agents' && <AgentsBoard theme={theme} />}
        {activeTab === 'evidence' && <EvidenceFeed theme={theme} />}
        {activeTab === 'findings' && renderFindings()}
        {activeTab === 'capabilities' && <CapabilitiesView theme={theme} />}
        {activeTab === 'config' && <ConfigView theme={theme} />}
      </Box>
    </Box>
  );
}

export default TabPanel;
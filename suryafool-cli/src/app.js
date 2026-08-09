// src/app.js
import React, { useEffect, useRef } from 'react';
import { FullScreenBox } from 'fullscreen-ink';
import { Text, Box } from 'ink';
import { StateProvider, useState, useDispatch } from './state/context.js';
import Header from './components/Header.js';
import Footer from './components/Footer.js';
import TabPanel from './components/TabPanel.js';
import CommandBar from './components/CommandBar.js';
import HelpOverlay from './components/HelpOverlay.js';
import ModalLayer from './components/ModalLayer.js';
import Console from './components/Console.js';
import { themes } from './styles/theme.js';
import BackendManager from './backend/backend.js';

function AppContent({ command, args, flags, theme: themeName }) {
  const theme = themes[themeName] || themes.cyberpunk;
  const state = useState();
  const dispatch = useDispatch();
  const backendRef = useRef(null);

  // Initialize backend manager once
  if (!backendRef.current) {
    backendRef.current = new BackendManager();
  }

  useEffect(() => {
    if (command) {
      // Add to history
      dispatch({ type: 'PUSH_HISTORY', payload: { command, args, time: new Date() } });
      
      // Execute command via backend - ensure args is an array
      const safeArgs = Array.isArray(args) ? args : [];
      backendRef.current.run(command, safeArgs, { 
        onOutput: (line) => {
          // Add each line of output to the console logs
          dispatch({ type: 'ADD_LOG', payload: line.trim() });
        }
      }).then((output) => {
        // Command completed successfully
        // For now, we'll just log completion - could parse output for findings/progress
        dispatch({ type: 'ADD_LOG', payload: `[${command}] Command completed` });
        
        // TODO: Parse output to update findings, progress, etc. based on command type
        if (command === 'doctor') {
          // Example: if doctor command succeeds, we could update some status
          dispatch({ type: 'ADD_LOG', payload: 'Environment check completed' });
        }
      }).catch((error) => {
        // Command failed
        dispatch({ type: 'ADD_LOG', payload: `[${command}] Error: ${error.message}` });
      });
    }
  }, [command, args, dispatch]);

  return (
    <FullScreenBox flexDirection="column">
      <Header theme={themeName} />
      <Box flexGrow={1} flexDirection="row">
        <Box flexGrow={2} flexDirection="column">
          <TabPanel theme={themeName} />
        </Box>
        <Box flexGrow={1}>
          <Console theme={themeName} />
        </Box>
      </Box>
      <Footer theme={themeName} />
      <CommandBar theme={themeName} />
      {state.modal && state.modal?.type === 'help' && <HelpOverlay theme={themeName} />}
      {state.modal && state.modal?.type !== 'help' && <ModalLayer theme={themeName} />}
    </FullScreenBox>
  );
}

function App(props) {
  return (
    <StateProvider>
      <AppContent {...props} />
    </StateProvider>
  );
}

export default App;
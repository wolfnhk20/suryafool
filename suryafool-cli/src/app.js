// src/app.js
import React, { useEffect } from 'react';
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
import BinaryManager from './backend/binary.js';
import BackendManager from './backend/backend.js';

function AppContent({ command, args, flags, theme: themeName }) {
  const theme = themes[themeName] || themes.cyberpunk;
  const state = useState();
  const dispatch = useDispatch();

  useEffect(() => {
    if (command) {
      dispatch({ type: 'PUSH_HISTORY', payload: { command, args, time: new Date() } });
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
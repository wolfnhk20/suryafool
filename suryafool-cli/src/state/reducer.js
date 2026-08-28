export const initialState = {
  activeTab: 'dashboard',
  dashboard: {
    findings: [],
    progress: 0,
  },
  agents: [],
  modal: null,
  theme: 'cyberpunk',
  logs: [],
  evidence: [],
  commandHistory: [],
  currentCommand: null,
  commandStatus: 'idle',
};

const handlers = {
  SET_TAB: (state, payload) => ({ ...state, activeTab: payload }),
  ADD_FINDING: (state, payload) => ({
    ...state,
    dashboard: { ...state.dashboard, findings: [...state.dashboard.findings, payload] },
  }),
  // Phase 2.7.8 — live evidence feed. Each EVIDENCE_CREATED event appends one
  // record; the list is bounded (newest 200) to keep long runs bounded.
  ADD_EVIDENCE: (state, payload) => ({
    ...state,
    evidence: [...state.evidence, payload].slice(-200),
  }),
  SET_PROGRESS: (state, payload) => ({
    ...state,
    dashboard: { ...state.dashboard, progress: payload },
  }),
  AGENT_STATUS: (state, payload) => ({ ...state, agents: payload }),
  SET_MODAL: (state, payload) => ({ ...state, modal: payload }),
  CLEAR_MODAL: (state) => ({ ...state, modal: null }),
  SET_THEME: (state, payload) => ({ ...state, theme: payload }),
  ADD_LOG: (state, payload) => {
    const logEntry = typeof payload === 'string' ? { level: 'info', message: payload, timestamp: Date.now() } : payload;
    return {
      ...state,
      logs: [...state.logs, logEntry],
    };
  },
  PUSH_HISTORY: (state, payload) => ({
    ...state,
    commandHistory: [...state.commandHistory, payload].slice(-100),
  }),
  SET_CURRENT_COMMAND: (state, payload) => ({ ...state, currentCommand: payload }),
  SET_COMMAND_STATUS: (state, payload) => ({ ...state, commandStatus: payload }),
  CLEAR_LOGS: (state) => ({ ...state, logs: [] }),
};

export function reducer(state = initialState, action) {
  const handler = handlers[action.type];
  return handler ? handler(state, action.payload) : state;
}
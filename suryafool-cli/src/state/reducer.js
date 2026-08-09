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
};

const handlers = {
  SET_TAB: (state, payload) => ({ ...state, activeTab: payload }),
  ADD_FINDING: (state, payload) => ({
    ...state,
    dashboard: { ...state.dashboard, findings: [...state.dashboard.findings, payload] },
  }),
  SET_PROGRESS: (state, payload) => ({
    ...state,
    dashboard: { ...state.dashboard, progress: payload },
  }),
  AGENT_STATUS: (state, payload) => ({ ...state, agents: payload }),
  SET_MODAL: (state, payload) => ({ ...state, modal: payload }),
  CLEAR_MODAL: (state) => ({ ...state, modal: null }),
  SET_THEME: (state, payload) => ({ ...state, theme: payload }),
  ADD_LOG: (state, payload) => ({
    ...state,
    logs: [...state.logs, payload],
  }),
};

export function reducer(state = initialState, action) {
  const handler = handlers[action.type];
  return handler ? handler(state, action.payload) : state;
}
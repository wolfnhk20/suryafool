import { createContext, useContext, useReducer } from 'react';
import { reducer, initialState } from './reducer.js';

export const StateContext = createContext(initialState);
export const DispatchContext = createContext(() => {});

export function StateProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  return (
    <StateContext.Provider value={state}>
      <DispatchContext.Provider value={dispatch}>
        {children}
      </DispatchContext.Provider>
    </StateContext.Provider>
  );
}

export function useState() {
  return useContext(StateContext);
}

export function useDispatch() {
  return useContext(DispatchContext);
}
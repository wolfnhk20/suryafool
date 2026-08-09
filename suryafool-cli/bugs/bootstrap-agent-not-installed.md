# Bug: Bootstrap Agent Not Installed

## Description
The Suryafool CLI application relies on the ootstrap.agent Python module to execute wireless scanning and exploration commands. In the current execution environment (opencode agent), this module is not installed, causing command execution to fail with a ModuleNotFoundError.

## Error Message
When attempting to run commands like doctor, explore, or scan, the following error appears in the console panel:
`
[doctor] Error: C:\Users\Shravani\AppData\Local\Programs\Python\Python39\python.exe: Error while finding module specification for 'bootstrap.agent' (ModuleNotFoundError: No module named 'bootstrap')
`

## Root Cause
The ootstrap.agent module is part of the Suryafool bootstrap agent implementation, which is designed to run on target hardware (ESP32, CC1101, etc.) or in a simulated environment. In the current development/opencode agent environment, this module is not available.

## Current Handling
The application gracefully handles this error by:
1. Capturing the exception in the backend execution chain
2. Displaying the error message in the console panel via the state management system
3. Allowing the user to continue interacting with the UI (switch tabs, enter new commands, etc.)

## Workaround for Development
To enable full functionality in a development environment:
1. Install the bootstrap agent dependencies (as per the bootstrap/manifest.yaml)
2. Or run the application in an environment where the bootstrap agent is available (e.g., on target hardware or a properly configured development VM)

## Notes
- This is not a bug in the Suryafool CLI codebase itself, but rather an environmental dependency issue.
- The CLI correctly reports the error and maintains UI responsiveness.
- In a production deployment with the required hardware and software stack, this error would not occur.

## Related Files
- src/app.js: Contains the backend execution logic that captures and displays errors
- src/backend/binary.js: Implements the fallback to python -m bootstrap.agent when the binary is not found
- src/backend/backend.js: Wrapper that calls the binary manager
- src/state/reducer.js: Handles the ADD_LOG action to display errors in the console

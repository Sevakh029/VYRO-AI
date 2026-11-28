# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.

## Mock signal states

Set `VITE_USE_MOCK_SIGNALS=true` in the dashboard environment to generate
IntersectionState updates for the network's signal IDs once per second. Mock
updates stop and are removed from the store when the first live intersection
message arrives. The generator is disabled by default.

## Command / acknowledgement log

The command log reads the existing WebSocket store and correlates canonical
`SignalCommand` and `ControllerAck` messages by `command_id`. Commands without
an acknowledgement become `timeout` after five seconds.

Set `VITE_USE_MOCK_COMMANDS=true` in the dashboard environment to generate
mock commands every two seconds, with acknowledgements delayed by about 300 ms.
Some mock commands are rejected or intentionally receive no acknowledgement.
Mock command generation is disabled and its entries are removed when the first
live command or acknowledgement arrives. The generator is disabled by default.

## Fleet KPI panel

The KPI panel prefers the latest metrics snapshot, or computes vehicle count,
mean speed, and stopped vehicles from the stored vehicle states until a live
snapshot is available. Set `VITE_USE_MOCK_KPIS=true` to generate mock metrics
snapshots once per second; generation stops when the first live snapshot arrives.
The generator is disabled by default.

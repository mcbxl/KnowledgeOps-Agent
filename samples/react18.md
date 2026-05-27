# React 18 Migration

React 18 recommends using `createRoot` from `react-dom/client` when creating a new root.

## Legacy Rendering

Older code examples may still use `ReactDOM.render`. In React 18 migration work, this should be treated as legacy guidance for new applications.

## Conflict Example

If one document says React 18 should use `createRoot` and another says new React 18 apps should use `ReactDOM.render`, the knowledge base should mark this as a version conflict.


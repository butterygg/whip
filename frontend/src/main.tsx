import React from "react";
import ReactDOM from "react-dom/client";
import * as Sentry from "@sentry/browser";
import { BrowserTracing } from "@sentry/tracing";

import App from "./App";
import "./index.css";

if (import.meta.env.VITE_SENTRY_DSN) {
  Sentry.init({
    dsn: import.meta.env.VITE_SENTRY_DSN,
    integrations: [new BrowserTracing()],
    tracesSampleRate: 1.0,
  });
}

const root = document.getElementById("root");

if (typeof root !== "undefined" && root !== null) {
  ReactDOM.createRoot(root).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
}

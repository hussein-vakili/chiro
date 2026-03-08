import React from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { readPortalConfig } from "./app/portalConfig";
import { createPortalQueryClient } from "./app/queryClient";
import "./styles.css";

const rootElement = document.getElementById("react-portal-root");

if (!rootElement) {
  throw new Error("React portal root element was not found.");
}

const config = readPortalConfig(rootElement);
const queryClient = createPortalQueryClient();

createRoot(rootElement).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename={config.routerBasename}>
        <App config={config} />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
);

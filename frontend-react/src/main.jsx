import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles.css";

const rootElement = document.getElementById("react-portal-root");
const config = {
  portalKind: rootElement?.dataset.portalKind || "client",
  routerBasename: rootElement?.dataset.routerBasename || "/app",
  sessionEndpoint: rootElement?.dataset.sessionEndpoint || "/api/client/session",
  staffDashboardEndpoint: rootElement?.dataset.staffDashboardEndpoint || "/api/staff/dashboard",
  dashboardEndpoint: rootElement?.dataset.dashboardEndpoint || "/api/client/dashboard",
  appointmentsEndpoint: rootElement?.dataset.appointmentsEndpoint || "/api/client/appointments/context",
  carePlanEndpoint: rootElement?.dataset.carePlanEndpoint || "/api/client/care-plan",
  messagesEndpoint: rootElement?.dataset.messagesEndpoint || "/api/client/messages",
  resultsEndpoint: rootElement?.dataset.resultsEndpoint || "/api/client/results",
  intakeEndpoint: rootElement?.dataset.intakeEndpoint || "/api/intake",
  saveIntakeEndpoint: rootElement?.dataset.saveIntakeEndpoint || "/api/intake",
  intakeEmbedEndpoint: rootElement?.dataset.intakeEmbedEndpoint || "/intake/embed",
  availabilityEndpoint: rootElement?.dataset.availabilityEndpoint || "/api/availability",
  bookAppointmentEndpoint: rootElement?.dataset.bookAppointmentEndpoint || "/api/appointments",
  cancelAppointmentBase: rootElement?.dataset.cancelAppointmentBase || "/api/client/appointments",
  spaRoot: rootElement?.dataset.spaRoot || "/app",
};

createRoot(rootElement).render(
  <React.StrictMode>
    <BrowserRouter basename={config.routerBasename}>
      <App config={config} />
    </BrowserRouter>
  </React.StrictMode>
);

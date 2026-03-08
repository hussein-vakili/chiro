export type PortalKind = "client" | "staff";

export interface PortalConfig {
  portalKind: PortalKind;
  routerBasename: string;
  sessionEndpoint: string;
  staffDashboardEndpoint: string;
  staffCalendarEndpoint: string;
  staffRemindersEndpoint: string;
  staffSettingsEndpoint: string;
  staffMessagesEndpoint: string;
  staffInvitationsEndpoint: string;
  staffCreateInvitationEndpoint: string;
  dashboardEndpoint: string;
  appointmentsEndpoint: string;
  carePlanEndpoint: string;
  messagesEndpoint: string;
  resultsEndpoint: string;
  intakeEndpoint: string;
  saveIntakeEndpoint: string;
  intakeEmbedEndpoint: string;
  availabilityEndpoint: string;
  bookAppointmentEndpoint: string;
  cancelAppointmentBase: string;
  spaRoot: string;
}

function dataValue(rootElement: HTMLElement | null, key: string, fallback: string): string {
  if (!rootElement) {
    return fallback;
  }
  const value = rootElement.dataset[key];
  return value && value.trim() ? value : fallback;
}

export function readPortalConfig(rootElement: HTMLElement | null): PortalConfig {
  const portalKind = dataValue(rootElement, "portalKind", "client") === "staff" ? "staff" : "client";
  return {
    portalKind,
    routerBasename: dataValue(rootElement, "routerBasename", portalKind === "staff" ? "/staff/app" : "/app"),
    sessionEndpoint: dataValue(rootElement, "sessionEndpoint", "/api/client/session"),
    staffDashboardEndpoint: dataValue(rootElement, "staffDashboardEndpoint", "/api/staff/dashboard"),
    staffCalendarEndpoint: dataValue(rootElement, "staffCalendarEndpoint", "/api/staff/calendar"),
    staffRemindersEndpoint: dataValue(rootElement, "staffRemindersEndpoint", "/api/staff/reminders"),
    staffSettingsEndpoint: dataValue(rootElement, "staffSettingsEndpoint", "/api/staff/settings"),
    staffMessagesEndpoint: dataValue(rootElement, "staffMessagesEndpoint", "/api/staff/messages"),
    staffInvitationsEndpoint: dataValue(rootElement, "staffInvitationsEndpoint", "/api/staff/invitations/new"),
    staffCreateInvitationEndpoint: dataValue(rootElement, "staffCreateInvitationEndpoint", "/api/staff/invitations"),
    dashboardEndpoint: dataValue(rootElement, "dashboardEndpoint", "/api/client/dashboard"),
    appointmentsEndpoint: dataValue(rootElement, "appointmentsEndpoint", "/api/client/appointments/context"),
    carePlanEndpoint: dataValue(rootElement, "carePlanEndpoint", "/api/client/care-plan"),
    messagesEndpoint: dataValue(rootElement, "messagesEndpoint", "/api/client/messages"),
    resultsEndpoint: dataValue(rootElement, "resultsEndpoint", "/api/client/results"),
    intakeEndpoint: dataValue(rootElement, "intakeEndpoint", "/api/intake"),
    saveIntakeEndpoint: dataValue(rootElement, "saveIntakeEndpoint", "/api/intake"),
    intakeEmbedEndpoint: dataValue(rootElement, "intakeEmbedEndpoint", "/intake/embed"),
    availabilityEndpoint: dataValue(rootElement, "availabilityEndpoint", "/api/availability"),
    bookAppointmentEndpoint: dataValue(rootElement, "bookAppointmentEndpoint", "/api/appointments"),
    cancelAppointmentBase: dataValue(rootElement, "cancelAppointmentBase", "/api/client/appointments"),
    spaRoot: dataValue(rootElement, "spaRoot", portalKind === "staff" ? "/staff/app" : "/app"),
  };
}

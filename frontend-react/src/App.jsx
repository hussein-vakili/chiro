import React, { useCallback, useEffect, useMemo, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { buildUrl, fetchJson } from "./shared/api";
import { copyText } from "./shared/browser";
import { formatMoney, toSpaPath } from "./shared/format";
import { useApiResource } from "./shared/hooks";
import { ErrorState, LoadingState, StatusPill } from "./shared/ui";
import ClinicOpsPage from "./features/staff/pages/ClinicOpsPage";
import LegacyEmbedPage from "./features/staff/pages/LegacyEmbedPage";
import PractitionerDashboardPage from "./features/staff/pages/PractitionerDashboardPage";
import AppointmentsPage from "./features/patient/pages/AppointmentsPage";
import CarePlanPage from "./features/patient/pages/CarePlanPage";
import DashboardPage from "./features/patient/pages/DashboardPage";
import IntakePage from "./features/patient/pages/IntakePage";
import MessagesPage from "./features/patient/pages/MessagesPage";
import ResultsPage from "./features/patient/pages/ResultsPage";
import StaffCalendarPage from "./features/staff/pages/StaffCalendarPage";
import StaffInvitationPage from "./features/staff/pages/StaffInvitationPage";
import StaffMessagesPage from "./features/staff/pages/StaffMessagesPage";
import StaffRemindersPage from "./features/staff/pages/StaffRemindersPage";
import StaffSettingsPage from "./features/staff/pages/StaffSettingsPage";

function PortalLayout({ session, config }) {
  return (
    <div className="rp-shell">
      <header className="rp-header">
        <div>
          <div className="rp-eyebrow">React patient portal</div>
          <h1>{session.user.first_name}, your portal is live.</h1>
          <p>
            This React workspace now sits on top of the same booking, care-plan, results, and messaging logic used by the
            clinic app.
          </p>
        </div>
        <div className="rp-header-card">
          <span>{session.ui_branding.clinic_name}</span>
          <strong>{session.user.display_name}</strong>
          <small>{session.user.email}</small>
        </div>
      </header>

      <nav className="rp-top-nav" aria-label="Portal sections">
        {session.nav.map((item) =>
          item.legacy ? (
            <a key={item.key} className="rp-top-link" href={item.url}>
              {item.label}
            </a>
          ) : (
            <NavLink
              key={item.key}
              className={({ isActive }) => `rp-top-link ${isActive ? "active" : ""}`.trim()}
              to={toSpaPath(item.url, config.routerBasename)}
              end={item.key === "dashboard"}
            >
              {item.label}
            </NavLink>
          )
        )}
      </nav>

      <Routes>
        <Route path="/" element={<DashboardPage config={config} session={session} />} />
        <Route path="/intake" element={<IntakePage config={config} />} />
        <Route path="/appointments" element={<AppointmentsPage config={config} session={session} />} />
        <Route path="/care-plan" element={<CarePlanPage config={config} />} />
        <Route path="/messages" element={<MessagesPage config={config} />} />
        <Route path="/results" element={<ResultsPage config={config} />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}

function StaffPortalLayout({ session, config }) {
  return (
    <div className="rp-shell">
      <header className="rp-header">
        <div>
          <div className="rp-eyebrow">React staff portal</div>
          <h1>{session.user.first_name}, clinic operations are live.</h1>
          <p>
            This workspace now runs the staff dashboard in React while keeping complex legacy screens available inside the
            same shell during the migration.
          </p>
        </div>
        <div className="rp-header-card">
          <span>{session.ui_branding.clinic_name}</span>
          <strong>{session.user.display_name}</strong>
          <small>{session.user.role === "clinician" ? "Practitioner access" : "Staff access"}</small>
        </div>
      </header>

      <nav className="rp-top-nav" aria-label="Staff sections">
        {session.nav.map((item) => (
          <NavLink
            key={item.key}
            className={({ isActive }) => `rp-top-link ${isActive ? "active" : ""}`.trim()}
            to={toSpaPath(item.url, config.routerBasename)}
            end={item.key === "dashboard"}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <Routes>
        <Route path="/" element={session.user.role === "clinician" ? <PractitionerDashboardPage config={config} /> : <ClinicOpsPage config={config} />} />
        <Route path="/clinic-ops" element={<ClinicOpsPage config={config} />} />
        <Route path="/calendar" element={<StaffCalendarPage config={config} />} />
        <Route path="/settings" element={<StaffSettingsPage config={config} />} />
        <Route path="/reminders" element={<StaffRemindersPage config={config} />} />
        <Route path="/journal" element={<LegacyEmbedPage src="/staff/journal?embed=1" title="Journal" detail="Practitioner journal remains on the legacy page for now." />} />
        <Route path="/learning" element={<LegacyEmbedPage src="/staff/learning?embed=1" title="Learning" detail="Learning content remains on the legacy page for now." />} />
        <Route path="/messaging" element={<StaffMessagesPage config={config} />} />
        <Route path="/new-invite" element={<StaffInvitationPage config={config} />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}

function LegacyRedirectPage({ to, label }) {
  useEffect(() => {
    window.location.assign(to);
  }, [to]);

  return <LoadingState title={`Opening ${label}`} detail="Handing you over to the legacy flow while this section is still being migrated." />;
}

export default function App({ config }) {
  const sessionResource = useApiResource(() => fetchJson(config.sessionEndpoint), [config.sessionEndpoint]);

  if (sessionResource.loading) {
    return <LoadingState detail="Checking your portal session and clinic settings." />;
  }

  if (sessionResource.error) {
    return <ErrorState detail={sessionResource.error} onRetry={sessionResource.reload} />;
  }

  if (config.portalKind === "staff") {
    return <StaffPortalLayout session={sessionResource.data} config={config} />;
  }

  return <PortalLayout session={sessionResource.data} config={config} />;
}

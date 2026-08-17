import { Navigate, Outlet, Route, Routes, useParams } from "react-router-dom";

import { ProtectedRoute } from "./components/ProtectedRoute";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { AppLayout } from "./layouts/AppLayout";
import { DashboardPage } from "./pages/DashboardPage";
import { LandingPage } from "./pages/LandingPage";
import { LoginPage } from "./pages/LoginPage";
import { NewRoleAnalysisPage } from "./pages/NewRoleAnalysisPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { RoleComparisonPage } from "./pages/RoleComparisonPage";
import { RoleDetailPage } from "./pages/RoleDetailPage";
import { RoleIntelligencePage } from "./pages/RoleIntelligencePage";
import { SettingsPage } from "./pages/SettingsPage";
import { SignupPage } from "./pages/SignupPage";
import { SkillsPage } from "./pages/SkillsPage";

function LegacyRoleRedirect() {
  const { roleId } = useParams();
  return <Navigate to={`/app/role-intelligence/${roleId}`} replace />;
}

function PublicOnlyRoute() {
  const { status } = useAuth();
  if (status === "authenticated") {
    return <Navigate to="/app" replace />;
  }
  return <Outlet />;
}

function AuthArea() {
  return (
    <AuthProvider>
      <Outlet />
    </AuthProvider>
  );
}

export function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />

      <Route element={<AuthArea />}>
        <Route element={<PublicOnlyRoute />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
        </Route>

        <Route path="/app" element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="role-intelligence" element={<RoleIntelligencePage />} />
            <Route path="role-intelligence/:roleId" element={<RoleDetailPage />} />
            <Route path="new-role-analysis" element={<NewRoleAnalysisPage />} />
            <Route path="compare" element={<RoleComparisonPage />} />
            <Route path="skills" element={<SkillsPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="/role-intelligence" element={<Navigate to="/app/role-intelligence" replace />} />
      <Route path="/role-intelligence/:roleId" element={<LegacyRoleRedirect />} />
      <Route path="/compare" element={<Navigate to="/app/compare" replace />} />
      <Route path="/new-role-analysis" element={<Navigate to="/app/new-role-analysis" replace />} />
      <Route path="/skills" element={<Navigate to="/app/skills" replace />} />
      <Route path="/settings" element={<Navigate to="/app/settings" replace />} />

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
import { Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./layouts/AppLayout";
import { DashboardPage } from "./pages/DashboardPage";
import { NewRoleAnalysisPage } from "./pages/NewRoleAnalysisPage";
import { RoleComparisonPage } from "./pages/RoleComparisonPage";
import { RoleDetailPage } from "./pages/RoleDetailPage";
import { RoleIntelligencePage } from "./pages/RoleIntelligencePage";
import { SettingsPage } from "./pages/SettingsPage";
import { SkillsPage } from "./pages/SkillsPage";

export function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="role-intelligence" element={<RoleIntelligencePage />} />
        <Route path="role-intelligence/:roleId" element={<RoleDetailPage />} />
        <Route path="compare" element={<RoleComparisonPage />} />
        <Route path="new-role-analysis" element={<NewRoleAnalysisPage />} />
        <Route path="skills" element={<SkillsPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

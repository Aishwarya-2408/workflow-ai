import { Suspense } from "react";
import { useRoutes, Routes, Route } from "react-router-dom";
import NotFound from "./components/NotFound";
import Layout from "./components/layout/Layout";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import ExcelWorkflowPage from "./pages/ExcelWorkflowPage";
import ImageWorkflowPage from "./pages/ImageWorkflowPage";
import WorkflowFilePreprocessingPage from "./pages/WorkflowFilePreprocessingPage";
import { Toaster } from "./components/ui/toaster";

function App() {
  const appRoutes = (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="workflow/excel/*" element={<ExcelWorkflowPage />} />
        <Route path="workflow/image/*" element={<ImageWorkflowPage />} />
        <Route path="workflow/file-preprocessing/*" element={<WorkflowFilePreprocessingPage />} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  );

  return (
    <Suspense fallback={<p>Loading...</p>}>
      {appRoutes}
      <Toaster />
    </Suspense>
  );
}

export default App;

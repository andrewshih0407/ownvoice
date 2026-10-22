import { Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Research } from "./pages/Research";
import { Screening } from "./pages/Screening";
import { Method } from "./pages/Method";
import { CodePage } from "./pages/CodePage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/research" replace />} />
        <Route path="/research" element={<Research />} />
        <Route path="/how" element={<Screening />} />
        <Route path="/method" element={<Method />} />
        <Route path="/code" element={<CodePage />} />
        <Route path="*" element={<Navigate to="/research" replace />} />
      </Route>
    </Routes>
  );
}

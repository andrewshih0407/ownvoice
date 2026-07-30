import { Routes, Route } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Home } from "./pages/Home";
import { Screening } from "./pages/Screening";
import { Method } from "./pages/Method";
import { CodePage } from "./pages/CodePage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/how" element={<Screening />} />
        <Route path="/method" element={<Method />} />
        <Route path="/code" element={<CodePage />} />
        <Route path="*" element={<Home />} />
      </Route>
    </Routes>
  );
}

import { Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import HomePage from "./pages/HomePage";
import ReportsPage from "./pages/ReportsPage";
import RecommendationsPage from "./pages/RecommendationsPage";
import "./App.css";

export default function App() {
  return (
    <div className="app">
      <Navbar />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/relatorios" element={<ReportsPage />} />
        <Route path="/recomendacoes" element={<RecommendationsPage />} />
      </Routes>
    </div>
  );
}

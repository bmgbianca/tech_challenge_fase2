import { useState } from "react";
import RouteLog from "./RouteLog";
import RouteSummary from "./RouteSummary";

const TABS = [
  { id: "log", label: "Log" },
  { id: "summary", label: "Resumo" },
];

export default function RightPanel({ snapshots, currentIndex, error, result }) {
  const [activeTab, setActiveTab] = useState("log");

  return (
    <aside className="right-panel">
      <div className="right-panel__tabs">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={`right-panel__tab${
              activeTab === tab.id ? " right-panel__tab--active" : ""
            }`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="right-panel__content">
        {activeTab === "log" ? (
          <RouteLog
            snapshots={snapshots}
            currentIndex={currentIndex}
            error={error}
          />
        ) : (
          <RouteSummary result={result} error={error} />
        )}
      </div>
    </aside>
  );
}

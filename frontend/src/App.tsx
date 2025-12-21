import { useState } from "react";
import DailyVisits from "./components/DailyVisits";
import HourlyVisits from "./components/HourlyVisits";
import VisitsKPI from "./components/VisitsKPI";
import ClicksKPI from "./components/ClicksKPI";
import ScrollDepthDistribution from "./components/ScrollDepthDistribution";
import "./App.css";

type Section = "overview" | "scroll" | "clicks" | "audience";
type TimeRange = 7 | 30;

export default function App() {
  const params = new URLSearchParams(window.location.search);
  const token = params.get("token") || "YOUR_DEFAULT_TOKEN";

  const [activeSection, setActiveSection] = useState<Section>("overview");
  const [timeRange, setTimeRange] = useState<TimeRange>(7);

  const scrollTo = (id: Section) => {
    setActiveSection(id);
    document.getElementById(id)?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  };

  return (
    <>
      <header className="topbar">
        <nav className="menu">
          <button
            className={activeSection === "overview" ? "active" : ""}
            onClick={() => scrollTo("overview")}
          >
            Основные метрики
          </button>
          <button
            className={activeSection === "scroll" ? "active" : ""}
            onClick={() => scrollTo("scroll")}
          >
            Глубина просмотра
          </button>
          <button
            className={activeSection === "clicks" ? "active" : ""}
            onClick={() => scrollTo("clicks")}
          >
            Взаимодействие
          </button>
          <button
            className={activeSection === "audience" ? "active" : ""}
            onClick={() => scrollTo("audience")}
          >
            Аудитория
          </button>
        </nav>

        <div className="time-range">
          <button
            className={timeRange === 7 ? "active" : ""}
            onClick={() => setTimeRange(7)}
          >
            7 дней
          </button>
          <button
            className={timeRange === 30 ? "active" : ""}
            onClick={() => setTimeRange(30)}
          >
            30 дней
          </button>
        </div>
      </header>

      <main className="page">
        <h1 className="site-title">example-site-1.tilda.ws</h1>

        {/* =====================
            OVERVIEW
        ===================== */}
        <section id="overview" className="section">
          <h2>Основные метрики</h2>

          <VisitsKPI token={token} days={timeRange} />

          <div className="charts-row">
            <div className="chart-col">
              <div className="chart-header">Визиты в день</div>
              <DailyVisits token={token} days={timeRange} />
            </div>

            <div className="chart-col">
              <div className="chart-header">
                Почасовые визиты (3 дня)
              </div>
              <HourlyVisits token={token} />
            </div>
          </div>
        </section>

        {/* =====================
            SCROLL DEPTH
        ===================== */}
        <section id="scroll" className="section">
          <h2>Глубина просмотра</h2>

          <ScrollDepthDistribution
            token={token}
            days={timeRange}
          />
        </section>

        {/* =====================
            CLICKS
        ===================== */}
        <section id="clicks" className="section">
          <h2>Взаимодействие с элементами</h2>

          {/* KPI по кликам */}
          <ClicksKPI token={token} days={timeRange} />

          <div className="placeholder">
            График кликов и топ элементов — далее
          </div>
        </section>

        {/* =====================
            AUDIENCE
        ===================== */}
        <section id="audience" className="section">
          <h2>Аудитория и устройства</h2>
          <div className="placeholder">
            Устройства, ОС, браузеры, гео
          </div>
        </section>
      </main>
    </>
  );
}

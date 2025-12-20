import { useState } from "react";
import VisitsOverTime from "./components/VisitsOverTime";
import "./App.css";

type Section = "overview" | "scroll" | "clicks" | "audience";
type TimeRange = "7days" | "30days";

export default function App() {
  const params = new URLSearchParams(window.location.search);
  const token = params.get("token") || "YOUR_DEFAULT_TOKEN";

  const [activeSection, setActiveSection] = useState<Section>("overview");
  const [timeRange, setTimeRange] = useState<TimeRange>("7days");

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
            className={timeRange === "7days" ? "active" : ""}
            onClick={() => setTimeRange("7days")}
          >
            7 дней
          </button>
          <button
            className={timeRange === "30days" ? "active" : ""}
            onClick={() => setTimeRange("30days")}
          >
            30 дней
          </button>
        </div>
      </header>

      <main className="page">
        <h1 className="site-title">example-site-1.tilda.ws</h1>

        <section id="overview" className="section">
          <h2>Основные метрики</h2>
          <div className="chart-block">
            <div className="chart-header">Визиты по времени</div>
            <VisitsOverTime token={token} range={timeRange} />
          </div>
        </section>

        <section id="scroll" className="section">
          <h2>Глубина просмотра</h2>
          <div className="placeholder">Распределение глубины, медиана, p75</div>
        </section>

        <section id="clicks" className="section">
          <h2>Взаимодействие с элементами</h2>
          <div className="placeholder">Клики, время до первого клика</div>
        </section>

        <section id="audience" className="section">
          <h2>Аудитория и устройства</h2>
          <div className="placeholder">Устройства, ОС, браузеры, гео</div>
        </section>
      </main>
    </>
  );
}

import { NavLink } from "react-router-dom";

export default function Navbar() {
  return (
    <header className="navbar">
      <div className="navbar__left">
        <div className="navbar__brand">
          <span className="navbar__logo">🚚</span>
          <div>
            <div className="navbar__title">RotaFácil</div>
            <div className="navbar__subtitle">Logística em movimento</div>
          </div>
        </div>

        <nav className="navbar__nav">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `navbar__link${isActive ? " navbar__link--active" : ""}`
            }
          >
            Início
          </NavLink>
          <NavLink
            to="/relatorios"
            className={({ isActive }) =>
              `navbar__link${isActive ? " navbar__link--active" : ""}`
            }
          >
            Relatórios
          </NavLink>
          <NavLink
            to="/recomendacoes"
            className={({ isActive }) =>
              `navbar__link${isActive ? " navbar__link--active" : ""}`
            }
          >
            Recomendações
          </NavLink>
        </nav>
      </div>

      <div className="navbar__user">
        <span>👤 Motorista</span>
        <span>🔔</span>
      </div>
    </header>
  );
}

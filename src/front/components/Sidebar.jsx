import { NavLink, useNavigate } from "react-router-dom";
import useGlobalReducer from "../hooks/useGlobalReducer";

const links = [
    { to: "/", label: "Inicio", icon: "fa-house", end: true },
    { to: "/clients", label: "Clientes", icon: "fa-users" },
    { to: "/activities", label: "Actividades", icon: "fa-list-check" },
    { to: "/billing", label: "Cierre de mes", icon: "fa-calendar-check" },
    { to: "/settings", label: "Ajustes", icon: "fa-gear" },
];

const initialsOf = (name) =>
    (name || "?")
        .split(" ")
        .map((word) => word[0])
        .slice(0, 2)
        .join("")
        .toUpperCase();

export const Sidebar = () => {
    const { store, dispatch } = useGlobalReducer();
    const navigate = useNavigate();
    const user = store.user;

    const logout = () => {
        dispatch({ type: "logout" });
        navigate("/login");
    };

    return (
        <aside className="io-sidebar">
            <NavLink to="/" className="io-brand">
                <span className="io-brand-mark">
                    <i className="fa-solid fa-check text-white"></i>
                </span>
                <span className="io-brand-name">InvoiceOps</span>
            </NavLink>

            <nav className="io-nav" aria-label="Principal">
                {links.map((link) => (
                    <NavLink key={link.to} to={link.to} end={link.end}>
                        <i className={`fa-solid ${link.icon}`}></i>
                        <span>{link.label}</span>
                    </NavLink>
                ))}
            </nav>

            <div className="flex-grow-1"></div>

            <div className="io-user d-flex flex-column gap-2">
                <div className="d-flex align-items-center gap-2 px-1">
                    <span className="io-avatar">{initialsOf(user?.full_name)}</span>
                    <span className="d-flex flex-column" style={{ minWidth: 0 }}>
                        <span className="fw-semibold text-truncate" style={{ fontSize: 14 }}>
                            {user?.full_name || "…"}
                        </span>
                        <span className="text-truncate" style={{ fontSize: 12, color: "var(--io-nav-text)" }}>
                            {user?.tenant_name || ""}
                        </span>
                    </span>
                </div>
                <button
                    type="button"
                    onClick={logout}
                    className="btn btn-link text-start p-1"
                    style={{ color: "var(--io-nav-text)", fontSize: 13 }}
                >
                    <i className="fa-solid fa-right-from-bracket me-2"></i>Cerrar sesión
                </button>
            </div>
        </aside>
    );
};
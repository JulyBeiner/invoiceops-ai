import { useEffect, useState } from "react";
import { Navigate, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { api } from "../api";
import useGlobalReducer from "../hooks/useGlobalReducer";
import { Sidebar } from "../components/Sidebar";

// Frame for every page inside the app: requires a token and loads the user.
// On narrow screens the sidebar is hidden and opens from the top bar button.
export const AppLayout = () => {
    const { store, dispatch } = useGlobalReducer();
    const navigate = useNavigate();
    const location = useLocation();
    const [menuOpen, setMenuOpen] = useState(false);

    // Close the mobile menu whenever the page changes.
    useEffect(() => {
        setMenuOpen(false);
    }, [location.pathname]);

    useEffect(() => {
        if (!store.token || store.user) return;
        api("/auth/me")
            .then((user) => dispatch({ type: "set_user", payload: user }))
            .catch(() => {
                dispatch({ type: "logout" });
                navigate("/login");
            });
    }, [store.token, store.user]);

    if (!store.token) return <Navigate to="/login" replace />;

    return (
        <div className="io-app">
            <header className="io-topbar">
                <NavLink to="/" className="io-brand">
                    <span className="io-brand-mark">
                        <i className="fa-solid fa-check text-white"></i>
                    </span>
                    <span className="io-brand-name">InvoiceOps</span>
                </NavLink>
                <button
                    type="button"
                    className="io-menu-btn"
                    aria-label="Abrir menú"
                    onClick={() => setMenuOpen(true)}
                >
                    <i className="fa-solid fa-bars"></i>
                </button>
            </header>

            {menuOpen && (
                <div className="io-backdrop" onClick={() => setMenuOpen(false)}></div>
            )}
            <Sidebar open={menuOpen} />

            <main className="io-main">
                <Outlet />
            </main>
        </div>
    );
};
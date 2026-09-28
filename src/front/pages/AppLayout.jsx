import { useEffect } from "react";
import { Navigate, Outlet, useNavigate } from "react-router-dom";
import { api } from "../api";
import useGlobalReducer from "../hooks/useGlobalReducer";
import { Sidebar } from "../components/Sidebar";

// Frame for every page inside the app: requires a token and loads the user.
export const AppLayout = () => {
    const { store, dispatch } = useGlobalReducer();
    const navigate = useNavigate();

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
            <Sidebar />
            <main className="io-main">
                <Outlet />
            </main>
        </div>
    );
};
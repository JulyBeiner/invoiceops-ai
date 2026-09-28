import {
  createBrowserRouter,
  createRoutesFromElements,
  Route,
} from "react-router-dom";
import { AuthLayout } from "./pages/AuthLayout";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { ForgotPassword } from "./pages/ForgotPassword";
import { ResetPassword } from "./pages/ResetPassword";
import { AppLayout } from "./pages/AppLayout";
import { Dashboard } from "./pages/Dashboard";
import { Clients } from "./pages/Clients";
import { Activities } from "./pages/Activities";

const NotFound = () => (
  <div className="p-5">
    <h1>Página no encontrada</h1>
  </div>
);

export const router = createBrowserRouter(
  createRoutesFromElements(
    <Route errorElement={<NotFound />}>
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
      </Route>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/clients" element={<Clients />} />
        <Route path="/activities" element={<Activities />} />
      </Route>
    </Route>
  )
);

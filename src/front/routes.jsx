import {
  createBrowserRouter,
  createRoutesFromElements,
  Route,
} from "react-router-dom";
import { AuthLayout } from "./pages/AuthLayout";
import { Login } from "./pages/Login";

const NotFound = () => (
  <div className="p-5">
    <h1>Página no encontrada</h1>
  </div>
);

// Temporary home until the app layout and dashboard exist.
const Placeholder = () => (
  <div className="p-5">
    <h1>Inicio</h1>
    <p>Has entrado. El menú y el panel llegan en el siguiente paso.</p>
  </div>
);

export const router = createBrowserRouter(
  createRoutesFromElements(
    <Route errorElement={<NotFound />}>
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<Login />} />
      </Route>
      <Route path="/" element={<Placeholder />} />
    </Route>
  )
);
import React from "react";
import { Routes, Route, Navigate, useNavigate, useParams, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext.jsx";
import { ProductProvider } from "./context/ProductContext.jsx";
import { CartProvider } from "./context/CartContext.jsx";
import { usePersistentState } from "./hooks/usePersistentState.js";
import ProtectedRoute from "./components/ProtectedRoute.jsx";

import RoleGate from "./pages/RoleGate.jsx";
import FarmerPortal from "./pages/FarmerPortal.jsx";
import ConsumerMarketplace from "./pages/ConsumerMarketplace.jsx";
import MarketInsights from "./pages/MarketInsights.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import DeveloperAccess from "./pages/DeveloperAccess.jsx";
import DeveloperDashboard from "./pages/DeveloperDashboard.jsx";
import UserProfile from "./pages/UserProfile.jsx";

function AppRoutes() {
  const { user, isAuthenticated, loading, logout } = useAuth();
  const [role, setRole] = usePersistentState("ks_role", null);
  const navigate = useNavigate();
  const location = useLocation();

  React.useEffect(() => {
    if (location.pathname === "/" && isAuthenticated) {
      if (user?.isDeveloper) {
        navigate("/developer", { replace: true });
      } else if (role === "farmer") {
        navigate("/farmer", { replace: true });
      } else if (role === "consumer") {
        navigate("/consumer", { replace: true });
      }
    }
  }, [location.pathname, isAuthenticated, user, role, navigate]);

  function switchRole() {
    setRole(null);
    navigate("/");
  }

  function handleLogout() {
    logout();             // clears state synchronously (see AuthContext)
    setRole(null);
    navigate("/", { replace: true });  // replace prevents Back from restoring protected URL
  }

  function enterRole(selectedRole) {
    setRole(selectedRole);
    if (isAuthenticated) {
      navigate(`/${selectedRole}`, { replace: true });
    } else {
      navigate(`/login/${selectedRole}`);
    }
  }

  if (loading) {
    return (
      <div
        className="min-h-screen w-full bg-[#14140F] text-[#C9A227] flex items-center justify-center"
        style={{ fontFamily: "'Work Sans', ui-sans-serif, system-ui, sans-serif" }}
      >
        <p className="font-serif text-lg">Loading…</p>
      </div>
    );
  }

  return (
    <Routes>
      {/* ─────────────────────────────────────────────────────────
       * Public routes
       * ───────────────────────────────────────────────────────── */}
      <Route
        path="/"
        element={
          isAuthenticated && user?.isDeveloper ? <Navigate to="/developer" replace /> :
          isAuthenticated && role === "farmer" ? <Navigate to="/farmer" replace /> :
          isAuthenticated && role === "consumer" ? <Navigate to="/consumer" replace /> :
          <RoleGate onSelect={enterRole} onLogout={handleLogout} />
        }
      />

      <Route
        path="/login/:roleParam"
        element={<LoginWrapper setRole={setRole} />}
      />

      <Route
        path="/register/:roleParam"
        element={<RegisterWrapper setRole={setRole} />}
      />

      <Route
        path="/developer-access"
        element={<DeveloperAccess onSwitchToLogin={() => navigate("/")} onBack={() => navigate("/")} />}
      />

      {/* ─────────────────────────────────────────────────────────
       * Protected routes — wrapped in ProtectedRoute
       * ───────────────────────────────────────────────────────── */}
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <UserProfile onSwitch={switchRole} onLogout={handleLogout} />
          </ProtectedRoute>
        }
      />

      <Route
        path="/insights"
        element={
          <ProtectedRoute>
            <MarketInsights onBack={() => navigate(-1)} />
          </ProtectedRoute>
        }
      />

      <Route
        path="/farmer"
        element={
          <ProtectedRoute>
            <ProductProvider scope="mine">
              <CartProvider>
                <FarmerPortal onSwitch={switchRole} onLogout={handleLogout} user={user} />
              </CartProvider>
            </ProductProvider>
          </ProtectedRoute>
        }
      />

      <Route
        path="/consumer"
        element={
          <ProtectedRoute>
            <ProductProvider scope="all">
              <CartProvider>
                <ConsumerMarketplace onSwitch={switchRole} onLogout={handleLogout} user={user} />
              </CartProvider>
            </ProductProvider>
          </ProtectedRoute>
        }
      />

      <Route
        path="/developer"
        element={
          <ProtectedRoute>
            <DeveloperDashboard onSwitch={switchRole} onLogout={handleLogout} user={user} />
          </ProtectedRoute>
        }
      />

      {/* Fallback — unknown routes go home */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

/* ───────────────────────────────────────────────────────────────
 * Wrapper helpers — extract useParams() for the component prop tree
 * ─────────────────────────────────────────────────────────────── */

function LoginWrapper({ setRole }) {
  const { roleParam } = useParams();
  const navigate = useNavigate();

  if (roleParam !== "farmer" && roleParam !== "consumer") {
    return <Navigate to="/" replace />;
  }

  return (
    <Login
      role={roleParam}
      onSwitchToRegister={() => navigate(`/register/${roleParam}`)}
      onSwitchToDeveloperAccess={() => navigate("/developer-access")}
      onSwitchRole={(targetRole) => {
        setRole(targetRole);
        navigate(`/login/${targetRole}`);
      }}
      onBack={() => {
        setRole(null);
        navigate("/");
      }}
    />
  );
}

function RegisterWrapper({ setRole }) {
  const { roleParam } = useParams();
  const navigate = useNavigate();

  if (roleParam !== "farmer" && roleParam !== "consumer") {
    return <Navigate to="/" replace />;
  }

  return (
    <Register
      role={roleParam}
      onSwitchToLogin={() => navigate(`/login/${roleParam}`)}
      onBack={() => {
        setRole(null);
        navigate("/");
      }}
    />
  );
}

function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}

export default App;

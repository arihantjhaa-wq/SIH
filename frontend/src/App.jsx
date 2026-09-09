import { AuthProvider, useAuth } from "./context/AuthContext.jsx";
import { ProductProvider } from "./context/ProductContext.jsx";
import { CartProvider } from "./context/CartContext.jsx";
import { usePersistentState } from "./hooks/usePersistentState.js";
import RoleGate from "./pages/RoleGate.jsx";
import FarmerPortal from "./pages/FarmerPortal.jsx";
import ConsumerMarketplace from "./pages/ConsumerMarketplace.jsx";
import MarketInsights from "./pages/MarketInsights.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import DeveloperAccess from "./pages/DeveloperAccess.jsx";
import DeveloperDashboard from "./pages/DeveloperDashboard.jsx";

function AuthedApp() {
  const { user, isAuthenticated, loading, logout } = useAuth();
  const [role, setRole] = usePersistentState("ks_role", null);
  const [authView, setAuthView] = usePersistentState(
    "ks_authView",
    "role-selection",
  );
  // Track if we're viewing Market Insights
  const [viewMarketInsights, setViewMarketInsights] = usePersistentState(
    "ks_marketInsights",
    false,
  );

  // ------------------------------------------------------------------
  // Helpers: navigate to a role-specific login and back
  // ------------------------------------------------------------------
  function enterRole(selectedRole) {
    setRole(selectedRole);
    setAuthView(
      selectedRole === "farmer" ? "farmer-login" : "consumer-login",
    );
  }

  function backToRoleSelection() {
    // Keep role hint so the landing page can pre-highlight, but do not
    // auto-redirect to portal — user wants to re-choose.
    setAuthView("role-selection");
  }

  // "Switch role" from inside a portal — clear the stored role so an
  // authenticated user can re-choose on the landing page.
  function switchRole() {
    setRole(null);
    setAuthView("role-selection");
  }

  // Cross-role switch from within a login page (e.g. Farmer → Consumer).
  function switchRoleTo(targetRole) {
    setRole(targetRole);
    setAuthView(
      targetRole === "farmer" ? "farmer-login" : "consumer-login",
    );
  }

  function handleLogout() {
    logout();
    // After logout, reset to the public landing page
    setRole(null);
    setAuthView("role-selection");
  }

  // ------------------------------------------------------------------
  // Loading
  // ------------------------------------------------------------------
  if (loading) {
    return (
      <div
        className="min-h-screen w-full bg-[#14140F] text-[#C9A227] flex items-center justify-center"
        style={{
          fontFamily: "'Work Sans', ui-sans-serif, system-ui, sans-serif",
        }}
      >
        <style>{`
          @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Work+Sans:wght@400;500;600&display=swap');
          .ff-display { font-family: 'Fraunces', ui-serif, Georgia, serif; }
        `}</style>
        <p className="ff-display text-lg">Loading…</p>
      </div>
    );
  }

  // ==================================================================
  // Authenticated: developer takes priority, then role → portal/marketplace
  // ==================================================================
  if (isAuthenticated) {
    // Developer/Admin — full marketplace visibility (server-authoritative).
    // This must check user flag, not a frontend role param, so a normal
    // farmer can never reach it by switching role or tampering routes.
    if (user?.isDeveloper) {
      return (
        <DeveloperDashboard
          onSwitch={switchRole}
          onLogout={handleLogout}
          user={user}
        />
      );
    }

    if (role === "farmer") {
      // Check if user wants Market Insights
      if (viewMarketInsights) {
        return (
          <MarketInsights
            onBack={() => {
              setViewMarketInsights(false);
              setRole("farmer");
            }}
          />
        );
      }

      return (
        <ProductProvider scope="mine">
          <CartProvider>
            <FarmerPortal
              onSwitch={switchRole}
              onLogout={handleLogout}
              user={user}
            />
          </CartProvider>
        </ProductProvider>
      );
    }

    if (role === "consumer") {
      // Check if user wants Market Insights
      if (viewMarketInsights) {
        return (
          <MarketInsights
            onBack={() => {
              setViewMarketInsights(false);
              setRole("consumer");
            }}
          />
        );
      }

      return (
        <ProductProvider scope="all">
          <CartProvider>
            <ConsumerMarketplace
              onSwitch={switchRole}
              onLogout={handleLogout}
              user={user}
            />
          </CartProvider>
        </ProductProvider>
      );
    }

    // Authenticated but no role stored — show landing to choose a path
    return <RoleGate onSelect={enterRole} onLogout={handleLogout} />;
  }

  // ==================================================================
  // Unauthenticated: public landing + role-specific auth
  // ==================================================================

  // Role-specific login pages
  if (authView === "farmer-login") {
    return (
      <Login
        role="farmer"
        onSwitchToRegister={() => setAuthView("farmer-register")}
        onSwitchToDeveloperAccess={() => setAuthView("developer")}
        onSwitchRole={switchRoleTo}
        onBack={backToRoleSelection}
      />
    );
  }

  if (authView === "consumer-login") {
    return (
      <Login
        role="consumer"
        onSwitchToRegister={() => setAuthView("consumer-register")}
        onSwitchToDeveloperAccess={() => setAuthView("developer")}
        onSwitchRole={switchRoleTo}
        onBack={backToRoleSelection}
      />
    );
  }

  // Register — return to the login for the role the user came from
  if (authView === "farmer-register" || authView === "consumer-register") {
    const returnTo = authView === "farmer-register" ? "farmer" : "consumer";
    return (
      <Register
        role={returnTo}
        onSwitchToLogin={() =>
          setAuthView(
            returnTo === "farmer" ? "farmer-login" : "consumer-login",
          )
        }
        onBack={backToRoleSelection}
      />
    );
  }

  // Legacy "register" value (pre-redesign localStorage) → farmer register
  if (authView === "register") {
    return (
      <Register
        role={role || "farmer"}
        onSwitchToLogin={() =>
          setAuthView(
            role === "consumer" ? "consumer-login" : "farmer-login",
          )
        }
        onBack={backToRoleSelection}
      />
    );
  }

  // Developer Access (accessible from either login)
  if (authView === "developer") {
    return (
      <DeveloperAccess
        onSwitchToLogin={() => {
          // Return to whichever login the user came from
          if (role === "consumer") setAuthView("consumer-login");
          else if (role === "farmer") setAuthView("farmer-login");
          else setAuthView("role-selection");
        }}
        onBack={backToRoleSelection}
      />
    );
  }

  // Default / fallback: public landing page
  return <RoleGate onSelect={enterRole} />;
}

function App() {
  return (
    <AuthProvider>
      <AuthedApp />
    </AuthProvider>
  );
}

export default App;

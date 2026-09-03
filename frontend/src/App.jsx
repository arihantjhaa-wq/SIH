import { AuthProvider, useAuth } from "./context/AuthContext.jsx";
import { ProductProvider } from "./context/ProductContext.jsx";
import { CartProvider } from "./context/CartContext.jsx";
import { usePersistentState } from "./hooks/usePersistentState.js";
import RoleGate from "./pages/RoleGate.jsx";
import FarmerPortal from "./pages/FarmerPortal.jsx";
import ConsumerMarketplace from "./pages/ConsumerMarketplace.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import DeveloperAccess from "./pages/DeveloperAccess.jsx";

function AuthedApp() {
  const { user, isAuthenticated, loading, logout } = useAuth();
  const [role, setRole] = usePersistentState("ks_role", null);
  const [authView, setAuthView] = usePersistentState("ks_authView", "login");

  if (loading) {
    return (
      <div
        className="min-h-screen w-full bg-[#14140F] text-[#C9A227] flex items-center justify-center"
        style={{ fontFamily: "'Work Sans', ui-sans-serif, system-ui, sans-serif" }}
      >
        <style>{`
          @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Work+Sans:wght@400;500;600&display=swap');
          .ff-display { font-family: 'Fraunces', ui-serif, Georgia, serif; }
        `}</style>
        <p className="ff-display text-lg">Loading…</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    if (authView === "register") {
      return (
        <Register
          onSwitchToLogin={() => setAuthView("login")}
          onBack={() => setAuthView("login")}
        />
      );
    }
    if (authView === "developer") {
      return (
        <DeveloperAccess
          onSwitchToLogin={() => setAuthView("login")}
          onBack={() => setAuthView("login")}
        />
      );
    }
    return (
      <Login
        onSwitchToRegister={() => setAuthView("register")}
        onSwitchToDeveloperAccess={() => setAuthView("developer")}
        onBack={() => setAuthView("login")}
      />
    );
  }

  return (
    <ProductProvider>
      <CartProvider>
        {!role && <RoleGate onSelect={setRole} onLogout={logout} user={user} />}

        {role === "farmer" && (
          <FarmerPortal
            onSwitch={() => setRole(null)}
            onLogout={logout}
            user={user}
          />
        )}

        {role === "consumer" && (
          <ConsumerMarketplace
            onSwitch={() => setRole(null)}
            onLogout={logout}
            user={user}
          />
        )}
      </CartProvider>
    </ProductProvider>
  );
}

function App() {
  return (
    <AuthProvider>
      <AuthedApp />
    </AuthProvider>
  );
}

export default App;

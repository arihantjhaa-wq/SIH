import { ProductProvider } from "./context/ProductContext.jsx";
import { CartProvider } from "./context/CartContext.jsx";
import { usePersistentState } from "./hooks/usePersistentState.js";
import RoleGate from "./pages/RoleGate.jsx";
import FarmerPortal from "./pages/FarmerPortal.jsx";
import ConsumerMarketplace from "./pages/ConsumerMarketplace.jsx";

function App() {
  const [role, setRole] = usePersistentState("ks_role", null);

  return (
    <ProductProvider>
      <CartProvider>
        {!role && <RoleGate onSelect={setRole} />}

        {role === "farmer" && <FarmerPortal onSwitch={() => setRole(null)} />}

        {role === "consumer" && (
          <ConsumerMarketplace onSwitch={() => setRole(null)} />
        )}
      </CartProvider>
    </ProductProvider>
  );
}

export default App;

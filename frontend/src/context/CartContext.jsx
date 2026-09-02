import React, { createContext, useContext, useState, useCallback } from "react";

const CartContext = createContext(null);

const STORAGE_KEY = "ks_cart";

function loadCart() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? JSON.parse(saved) : {};
  } catch {
    return {};
  }
}

export function CartProvider({ children }) {
  const [cart, setCart] = useState(loadCart);

  const persist = useCallback((next) => {
    setCart(next);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      // ignore quota errors
    }
  }, []);

  const addToCart = useCallback(
    (productId, qty) => {
      persist((prev) => ({
        ...prev,
        [productId]: (prev[productId] || 0) + qty,
      }));
    },
    [persist],
  );

  const setQty = useCallback(
    (productId, qty) => {
      persist((prev) => {
        const next = { ...prev };
        if (qty <= 0) {
          delete next[productId];
        } else {
          next[productId] = qty;
        }
        return next;
      });
    },
    [persist],
  );

  const removeFromCart = useCallback(
    (productId) => {
      persist((prev) => {
        const next = { ...prev };
        delete next[productId];
        return next;
      });
    },
    [persist],
  );

  const clearCart = useCallback(() => {
    persist({});
  }, [persist]);

  const value = { cart, addToCart, setQty, removeFromCart, clearCart };

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  const ctx = useContext(CartContext);
  if (!ctx) {
    throw new Error("useCart must be used within a CartProvider");
  }
  return ctx;
}

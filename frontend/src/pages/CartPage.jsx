import React, { useState, useMemo } from "react";
import { ShoppingCart, ArrowLeft, Plus, Minus, Trash2, Truck, CircleCheck as CheckCircle2 } from "lucide-react";
import { money } from "../utils/marketplace.js";
import ProductPhoto from "../components/ProductPhoto.jsx";

export default function CartPage({
  cartLines,
  isBusiness,
  bizUnlocked,
  priceFor,
  subtotal,
  savings,
  bizUnlockedSavings,
  setQty,
  removeFromCart,
  onBack,
}) {
  const [orderPlaced, setOrderPlaced] = useState(false);

  if (orderPlaced) {
    return (
      <main className="max-w-3xl mx-auto px-5 py-10">
        <div className="border border-[#E4D6A7] bg-[#FBF7EC] px-6 py-16 text-center">
          <CheckCircle2 className="w-10 h-10 text-[#1B3A2B] mx-auto mb-4" />
          <h1 className="ff-display text-2xl mb-2">Order placed!</h1>
          <p className="text-sm text-[#5C5842]">
            Your order of {money(subtotal)} has been received. The farmer will
            be notified and your produce will be on its way.
          </p>
          <button
            onClick={() => {
              setOrderPlaced(false);
              onBack();
            }}
            className="mt-4 px-4 py-2 text-sm border border-[#1B3A2B] text-[#1B3A2B] hover:bg-[#1B3A2B] hover:text-[#F3ECDD] transition-colors"
          >
            Back to shopping
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="max-w-3xl mx-auto px-5 py-10">
      <button
        onClick={onBack}
        className="flex items-center gap-1.5 text-sm text-[#5C5842] hover:text-[#1B3A2B] transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" /> Continue shopping
      </button>

      <div className="flex items-center gap-2 mt-6 mb-6">
        <ShoppingCart className="w-5 h-5 text-[#1B3A2B]" />
        <h1 className="ff-display text-3xl">Your order</h1>
      </div>

      {cartLines.length === 0 ? (
        <div className="border border-[#E4D6A7] bg-[#FBF7EC] px-6 py-16 text-center">
          <p className="text-sm text-[#5C5842]">
            Nothing added yet — head back to the catalogue to start an order.
          </p>
          <button
            onClick={onBack}
            className="mt-4 px-4 py-2 text-sm border border-[#1B3A2B] text-[#1B3A2B] hover:bg-[#1B3A2B] hover:text-[#F3ECDD] transition-colors"
          >
            Browse products
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="md:col-span-2 space-y-4">
            {cartLines.map(({ product, qty }) => (
              <div
                key={product.id}
                className="flex items-start gap-3 text-sm border border-[#E4D6A7] bg-[#FBF7EC] p-3"
              >
                <ProductPhoto
                  product={product}
                  className="w-16 h-16 object-cover shrink-0"
                />
                <div className="flex-1">
                  <p className="ff-display text-base leading-tight">
                    {product.name}
                  </p>
                  <p className="text-xs text-[#5C5842] mt-1">
                    {product.farmer}
                  </p>
                  <p className="text-xs text-[#5C5842] tabular mt-1">
                    {qty} {product.unit} × {money(priceFor(product))}
                  </p>
                  {isBusiness && (
                    <p className="text-[11px] text-[#8A6D1E] mt-0.5">
                      Min order {product.minBulkQty} {product.unit}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setQty(product, qty - (isBusiness ? 5 : 1))}
                    className="w-7 h-7 flex items-center justify-center border border-[#D8CBA1] hover:border-[#1B3A2B] active:bg-[#1B3A2B] active:text-[#F3ECDD]"
                  >
                    <Minus className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => setQty(product, qty + (isBusiness ? 5 : 1))}
                    className="w-7 h-7 flex items-center justify-center border border-[#D8CBA1] hover:border-[#1B3A2B] active:bg-[#1B3A2B] active:text-[#F3ECDD]"
                  >
                    <Plus className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => removeFromCart(product.id)}
                    className="w-7 h-7 flex items-center justify-center text-[#8C2E33] hover:text-[#6B1E2B]"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="border border-[#E4D6A7] bg-[#FBF7EC] p-4 h-fit">
            <h2 className="ff-display text-lg mb-3">Summary</h2>
            <div className="text-sm space-y-1">
              <div className="flex justify-between tabular">
                <span className="text-[#5C5842]">Subtotal</span>
                <span>{money(subtotal)}</span>
              </div>
              {bizUnlockedSavings && (
                <div className="flex justify-between tabular text-[#1B3A2B]">
                  <span>Business savings</span>
                  <span>− {money(savings)}</span>
                </div>
              )}
              <div className="flex items-center gap-1.5 text-xs text-[#5C5842] pt-2">
                <Truck className="w-3.5 h-3.5" />
                {isBusiness
                  ? "Freight quoted at checkout for bulk orders"
                  : "Delivered within 2 days"}
              </div>
            </div>

            <button
              onClick={() => setOrderPlaced(true)}
              className="w-full mt-4 py-2.5 bg-[#1B3A2B] text-[#F3ECDD] text-sm hover:bg-[#14140F] active:bg-[#0E1F17] transition-colors"
            >
              Proceed to checkout
            </button>
          </div>
        </div>
      )}
    </main>
  );
}

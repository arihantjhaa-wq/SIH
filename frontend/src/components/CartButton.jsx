import React from "react";
import { ShoppingCart } from "lucide-react";

export default function CartButton({ count, onClick, active }) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={`relative flex items-center gap-2 px-4 py-2 text-sm border border-[#C9A227] transition-colors ${
        active
          ? "bg-[#C9A227] text-[#14140F]"
          : "text-[#F3ECDD] hover:bg-[#C9A227] hover:text-[#14140F]"
      }`}
    >
      <ShoppingCart className="w-4 h-4" />
      Cart
      {count > 0 && (
        <span className="absolute -top-2 -right-2 min-w-4.5 h-4.5 px-1 flex items-center justify-center rounded-full bg-[#C9A227] text-[#14140F] text-[10px] font-semibold">
          {count}
        </span>
      )}
    </button>
  );
}

import React from "react";
import { ShoppingCart } from "lucide-react";
import { LiquidButton } from "./ui/liquid-glass-button";

export default function CartButton({ count, onClick, active }) {
  return (
    <span className="relative inline-flex">
      <LiquidButton
        label="Cart"
        icon={<ShoppingCart className="w-4 h-4" />}
        onClick={onClick}
        size="sm"
        className={active ? "bg-[#C9A227] text-[#14140F]" : ""}
      />
      {count > 0 && (
        <span className="absolute -top-1.5 -right-1.5 min-w-[18px] h-[18px] flex items-center justify-center rounded-full bg-[#C4544A] text-white text-[10px] font-medium leading-none px-1">
          {count > 99 ? "99+" : count}
        </span>
      )}
    </span>
  );
}

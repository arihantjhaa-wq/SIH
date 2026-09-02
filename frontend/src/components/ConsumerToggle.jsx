import React from "react";
import { User, Building2 } from "lucide-react";

export default function ConsumerToggle({ consumerType, onChange }) {
  const household = consumerType === "individual";
  const business = consumerType === "business";
  return (
    <div className="inline-flex border border-[#4A4630] w-full sm:w-auto">
      <button
        onClick={() => onChange("individual")}
        aria-pressed={household}
        className={`flex-1 sm:flex-none flex items-center justify-center gap-1.5 px-4 py-2 text-sm transition-colors ${
          household
            ? "bg-[#C9A227] text-[#14140F] shadow-[inset_0_0_0_1px_#F3ECDD]"
            : "bg-transparent text-[#C9C3AE] hover:bg-[#1D1C14]"
        }`}
      >
        <User className="w-3.5 h-3.5" /> Household
      </button>
      <button
        onClick={() => onChange("business")}
        aria-pressed={business}
        className={`flex-1 sm:flex-none flex items-center justify-center gap-1.5 px-4 py-2 text-sm transition-colors border-l border-[#4A4630] ${
          business
            ? "bg-[#1B3A2B] text-[#F3ECDD] shadow-[inset_0_0_0_1px_#C9A227]"
            : "bg-transparent text-[#C9C3AE] hover:bg-[#1D1C14]"
        }`}
      >
        <Building2 className="w-3.5 h-3.5" /> Business
      </button>
    </div>
  );
}

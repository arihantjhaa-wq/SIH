import React from "react";
import { User, Building2 } from "lucide-react";
import { LiquidButton } from "./ui/liquid-glass-button";

export default function ConsumerToggle({ consumerType, onChange }) {
  const household = consumerType === "individual";
  const business = consumerType === "business";
  return (
    <div className="inline-flex gap-2 w-full sm:w-auto">
      <LiquidButton
        label="Household"
        icon={<User className="w-3.5 h-3.5" />}
        onClick={() => onChange("individual")}
        size="sm"
        className={household ? "bg-[#C9A227] text-[#14140F]" : ""}
      />
      <LiquidButton
        label="Business"
        icon={<Building2 className="w-3.5 h-3.5" />}
        onClick={() => onChange("business")}
        size="sm"
        className={business ? "bg-[#1B3A2B] text-[#F3ECDD]" : ""}
      />
    </div>
  );
}

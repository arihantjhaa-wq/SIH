import { LiquidButton } from "@/components/ui/liquid-glass-button";

export default function DemoOne() {
  return (
    <div className="flex flex-wrap items-center gap-3 p-6 bg-[#14140F] min-h-[240px]">
      <LiquidButton label="Pearl" />
      <LiquidButton label="Start selling" />
      <LiquidButton label="Browse the market" />
      <LiquidButton label="Sign in" size="lg" />
      <LiquidButton label="Small" size="sm" />
      <LiquidButton label="Large" size="xl" />
    </div>
  );
}

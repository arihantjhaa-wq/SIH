import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

export const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 cursor-pointer select-none",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90 active:scale-[0.98]",
        destructive:
          "bg-destructive text-destructive-foreground hover:bg-destructive/90 active:scale-[0.98]",
        outline:
          "border border-input bg-background hover:bg-accent hover:text-accent-foreground active:scale-[0.98]",
        secondary:
          "bg-secondary text-secondary-foreground hover:bg-secondary/80 active:scale-[0.98]",
        ghost: "hover:bg-accent hover:text-accent-foreground active:scale-[0.98]",
        link: "text-primary underline-offset-4 hover:underline",
        cool: "bg-gradient-to-b from-[#222] to-[#111] text-[#F3ECDD] shadow-[0_2px_12px_rgba(0,0,0,0.6),inset_0_1px_0_rgba(255,255,255,0.08)] hover:from-[#2a2a2a] hover:to-[#181818] hover:shadow-[0_4px_16px_rgba(0,0,0,0.7),inset_0_1px_0_rgba(255,255,255,0.1)] active:from-[#111] active:to-[#0a0a0a] active:shadow-[inset_0_2px_4px_rgba(0,0,0,0.5)] active:translate-y-px",
      },
      size: {
        xs: "h-6 rounded-sm px-2 text-[11px]",
        sm: "h-8 rounded-md px-3 text-xs",
        default: "h-9 px-4 py-2",
        md: "h-9 rounded-md px-4 py-2",
        lg: "h-10 rounded-md px-8 text-base",
        xl: "h-11 rounded-md px-8 text-base",
        xxl: "h-12 rounded-lg px-8 text-base font-semibold tracking-wide",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "xxl",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

/* ── LiquidButton ────────────────────────────────────────────── */
export interface LiquidButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  label?: string;
  icon?: React.ReactNode;
  decor?: boolean;
}

const LiquidButton = React.forwardRef<HTMLButtonElement, LiquidButtonProps>(
  (
    {
      className,
      variant = "default",
      size = "xxl",
      asChild = false,
      label,
      icon,
      decor: _decor,
      children,
      type = "button",
      disabled = false,
      ...props
    },
    ref
  ) => {
    const Comp = asChild ? Slot : "button";
    const content = children ?? label ?? "";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        type={type}
        disabled={disabled}
        {...props}
      >
        {icon}
        {content}
      </Comp>
    );
  }
);
LiquidButton.displayName = "LiquidButton";

/* ── MetalButton ─────────────────────────────────────────────── */
export interface MetalButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  label?: string;
  icon?: React.ReactNode;
  decor?: boolean;
}

const MetalButton = React.forwardRef<HTMLButtonElement, MetalButtonProps>(
  (
    {
      className,
      variant = "cool",
      size = "xxl",
      asChild = false,
      label,
      icon,
      decor: _decor,
      children,
      type = "button",
      disabled = false,
      ...props
    },
    ref
  ) => {
    const Comp = asChild ? Slot : "button";
    const content = children ?? label ?? "";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        type={type}
        disabled={disabled}
        {...props}
      >
        {icon}
        {content}
      </Comp>
    );
  }
);
MetalButton.displayName = "MetalButton";

export { Button, LiquidButton, MetalButton };

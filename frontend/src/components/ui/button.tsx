import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-full text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [touch-action:manipulation]",
  {
    variants: {
      variant: {
        default:
          "bg-[#0071e3] text-white shadow-sm hover:bg-[#0077ed] active:bg-[#006edb]",
        destructive:
          "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline:
          "border border-black/10 bg-white text-foreground hover:bg-black/[0.03]",
        secondary:
          "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-black/[0.04] hover:text-foreground",
        link: "text-[#0071e3] underline-offset-4 hover:underline",
        neon: "bg-gradient-to-b from-[#0077ed] to-[#0071e3] text-white shadow-sm hover:opacity-95",
      },
      size: {
        default: "h-11 px-5 py-2",
        sm: "h-9 rounded-full px-4 text-sm md:h-9",
        lg: "h-12 rounded-full px-8 text-base",
        icon: "h-11 w-11 shrink-0 rounded-full",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

// CVA variants are consumed by other components; Fast Refresh only applies to pure component files.
export { Button, buttonVariants } // eslint-disable-line react-refresh/only-export-components

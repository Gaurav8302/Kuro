import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 font-rajdhani tracking-wide",
  {
    variants: {
      variant: {
        default: "glass-panel border-holo-cyan-400/30 text-holo-cyan-300 hover:shadow-holo-glow hover:border-holo-cyan-400/50",
        destructive:
          "glass-panel border-holo-magenta-400/30 text-holo-magenta-300 hover:shadow-holo-magenta hover:border-holo-magenta-400/50",
        outline:
          "glass-panel border-holo-cyan-400/20 text-holo-cyan-400 hover:bg-holo-cyan-500/10 hover:border-holo-cyan-400/40",
        secondary:
          "glass-panel border-holo-purple-400/30 text-holo-purple-300 hover:shadow-holo-purple hover:border-holo-purple-400/50",
        accent:
          "glass-panel border-holo-blue-400/30 text-holo-blue-300 hover:shadow-holo-blue hover:border-holo-blue-400/50",
        ghost: "bg-transparent text-holo-cyan-400 hover:bg-holo-cyan-500/10 hover:shadow-holo-glow",
        link: "text-holo-cyan-400 underline-offset-4 hover:underline hover:text-holo-glow",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        xl: "h-14 rounded-lg px-12 text-lg",
        icon: "h-10 w-10",
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

export { Button, buttonVariants }

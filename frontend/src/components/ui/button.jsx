import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva } from 'class-variance-authority'
import { Loader2 } from 'lucide-react'

import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-semibold transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 active:scale-[.98]',
  {
    variants: {
      variant: {
        // Flat fills. A gradient on a button is the single loudest tell of a
        // generated template, and it costs contrast at the light end.
        default:
          'bg-primary text-primary-foreground shadow-soft hover:bg-primary/90',
        secondary:
          'bg-secondary text-secondary-foreground hover:bg-secondary/80 shadow-soft',
        outline:
          'border border-border bg-card text-foreground shadow-soft hover:bg-muted',
        ghost: 'text-foreground hover:bg-muted',
        subtle: 'bg-primary/10 text-primary hover:bg-primary/15',
        accent: 'bg-accent text-accent-foreground shadow-soft hover:bg-accent/90',
        destructive:
          'bg-destructive text-destructive-foreground shadow-soft hover:bg-destructive/90',
        success: 'bg-success text-success-foreground shadow-soft hover:bg-success/90',
        link: 'text-primary underline-offset-4 hover:underline',
      },
      size: {
        // `default` and up clear 44px so primary actions are comfortable to tap;
        // sm/xs/icon-sm stay compact for dense rows and toolbars.
        default: 'h-11 px-4 py-2',
        sm: 'h-9 rounded-lg px-3 text-[13px]',
        xs: 'h-8 rounded-lg px-2.5 text-xs [&_svg]:size-3.5',
        lg: 'h-12 rounded-xl px-7 text-base',
        icon: 'size-11',
        'icon-sm': 'size-9 rounded-lg [&_svg]:size-4',
      },
    },
    defaultVariants: { variant: 'default', size: 'default' },
  },
)

const Button = React.forwardRef(
  (
    { className, variant, size, asChild = false, loading = false, children, ...props },
    ref,
  ) => {
    const Comp = asChild ? Slot : 'button'
    if (asChild) {
      return (
        <Comp
          className={cn(buttonVariants({ variant, size, className }))}
          ref={ref}
          {...props}
        >
          {children}
        </Comp>
      )
    }
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={props.disabled || loading}
        {...props}
      >
        {loading && <Loader2 className="animate-spin" aria-hidden="true" />}
        {children}
      </Comp>
    )
  },
)
Button.displayName = 'Button'

export { Button, buttonVariants }

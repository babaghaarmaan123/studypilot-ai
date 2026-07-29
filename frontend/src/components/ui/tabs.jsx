import * as React from 'react'
import * as TabsPrimitive from '@radix-ui/react-tabs'

import { cn } from '@/lib/utils'

const Tabs = TabsPrimitive.Root

/**
 * Scrollable tab strip.
 *
 * Six tabs need about 570px of room, so on a phone they have to scroll. The
 * pill-inside-a-tray look made that read as broken: the tray clipped mid-label
 * with no hint there was more. On small screens this drops the tray, sits the
 * tabs on an underline, and lets them scroll with snap points and a fading
 * right edge so it is obvious the row continues. From `sm` up, where everything
 * fits, it goes back to the contained pill style.
 */
const TabsList = React.forwardRef(({ className, ...props }, ref) => (
  <div className="relative -mx-1 px-1">
    <TabsPrimitive.List
      ref={ref}
      className={cn(
        'flex w-full items-center justify-start gap-1 overflow-x-auto scroll-smooth',
        // Hide the scrollbar itself; the fade and snap communicate scrollability.
        '[-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden',
        'snap-x snap-mandatory scroll-pl-1',
        'border-b border-border pb-1 text-muted-foreground',
        'sm:w-auto sm:snap-none sm:rounded-xl sm:border-0 sm:bg-muted sm:p-1 sm:pb-1',
        className,
      )}
      {...props}
    />
    {/* Fades the cut-off tab instead of slicing it. */}
    <span
      aria-hidden="true"
      className="pointer-events-none absolute inset-y-0 right-0 w-6 bg-gradient-to-l from-background to-transparent sm:hidden"
    />
  </div>
))
TabsList.displayName = TabsPrimitive.List.displayName

const TabsTrigger = React.forwardRef(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      // min-h-11 gives a 44px tap target; shrink-0 stops labels wrapping to two
      // lines, which is what made the old strip look cramped.
      'inline-flex min-h-11 shrink-0 snap-start items-center justify-center gap-1.5 whitespace-nowrap rounded-lg px-3 text-sm font-semibold transition-all',
      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50',
      // Underline on mobile, pill from sm up.
      'border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:text-primary',
      'sm:min-h-9 sm:border-b-0 sm:data-[state=active]:bg-card sm:data-[state=active]:text-foreground sm:data-[state=active]:shadow-soft',
      '[&_svg]:size-4',
      className,
    )}
    {...props}
  />
))
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName

const TabsContent = React.forwardRef(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn(
      'mt-5 focus-visible:outline-none data-[state=active]:animate-fade-up',
      className,
    )}
    {...props}
  />
))
TabsContent.displayName = TabsPrimitive.Content.displayName

export { Tabs, TabsList, TabsTrigger, TabsContent }

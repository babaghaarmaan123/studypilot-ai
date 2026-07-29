import * as React from 'react'
import * as AvatarPrimitive from '@radix-ui/react-avatar'

import { cn, initials } from '@/lib/utils'
import { assetUrl } from '@/lib/api'

const Avatar = React.forwardRef(({ className, ...props }, ref) => (
  <AvatarPrimitive.Root
    ref={ref}
    className={cn(
      'relative flex size-10 shrink-0 overflow-hidden rounded-full',
      className,
    )}
    {...props}
  />
))
Avatar.displayName = AvatarPrimitive.Root.displayName

const AvatarImage = React.forwardRef(({ className, ...props }, ref) => (
  <AvatarPrimitive.Image
    ref={ref}
    className={cn('aspect-square size-full object-cover', className)}
    {...props}
  />
))
AvatarImage.displayName = AvatarPrimitive.Image.displayName

const AvatarFallback = React.forwardRef(({ className, ...props }, ref) => (
  <AvatarPrimitive.Fallback
    ref={ref}
    className={cn(
      'flex size-full items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground',
      className,
    )}
    {...props}
  />
))
AvatarFallback.displayName = AvatarPrimitive.Fallback.displayName

/** The avatar as used throughout the app: photo if set, initials otherwise. */
function UserAvatar({ user, className }) {
  const src = assetUrl(user?.avatar_url)
  return (
    <Avatar className={className}>
      {src && <AvatarImage src={src} alt={user?.name || 'Profile picture'} />}
      <AvatarFallback>{initials(user?.name)}</AvatarFallback>
    </Avatar>
  )
}

export { Avatar, AvatarImage, AvatarFallback, UserAvatar }

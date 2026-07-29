import { motion } from 'framer-motion'
import { Award, Flame, Lock, Star, Trophy } from 'lucide-react'

import { useFetch } from '@/hooks/useFetch'
import api from '@/lib/api'
import { cn, iconFor, pluralise } from '@/lib/utils'

import { PageHeader } from '@/components/PageHeader'
import { StatCard } from '@/components/StatCard'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { EmptyState } from '@/components/ui/empty-state'
import { Progress } from '@/components/ui/progress'
import { SkeletonList, SkeletonStats } from '@/components/ui/skeleton'

const TIER_VARIANTS = {
  bronze: 'warning',
  silver: 'secondary',
  gold: 'success',
  platinum: 'violet',
}

export default function Achievements() {
  const { data, loading, error } = useFetch(() => api.achievements.list(), [])

  if (error) {
    return (
      <EmptyState icon={Trophy} title="Couldn't load achievements" description={error.message} />
    )
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Achievements"
        description="XP, streaks and badges that keep your motivation high."
        icon={Trophy}
      />

      {loading || !data ? (
        <SkeletonStats />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Level"
            value={data.level}
            hint={`${data.xp_into_level}/${data.xp_for_next_level} XP to next level`}
            progress={(data.xp_into_level / data.xp_for_next_level) * 100}
            icon={Star}
            tone="violet"
          />
          <StatCard label="Total XP" value={data.xp} icon={Award} tone="indigo" />
          <StatCard
            label="Badges unlocked"
            value={`${data.unlocked_count}/${data.total_count}`}
            progress={(data.unlocked_count / data.total_count) * 100}
            icon={Trophy}
            tone="amber"
          />
          <StatCard
            label="Study streak"
            value={pluralise(data.streak_current, 'day')}
            hint={`Longest: ${pluralise(data.streak_longest, 'day')}`}
            icon={Flame}
            tone="emerald"
          />
        </div>
      )}

      {loading ? (
        <SkeletonList rows={5} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data?.achievements.map((achievement, index) => {
            const Icon = iconFor(achievement.icon, 'Award')
            return (
              <motion.div
                key={achievement.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(index * 0.03, 0.4) }}
              >
                <Card
                  className={cn(
                    'card-hover h-full p-5',
                    !achievement.unlocked && 'opacity-70 grayscale',
                  )}
                >
                  <div className="flex items-start justify-between gap-3">
                    <span
                      className={cn(
                        'grid size-12 shrink-0 place-items-center rounded-2xl',
                        achievement.unlocked
                          ? 'bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-glow'
                          : 'bg-muted text-muted-foreground',
                      )}
                    >
                      {achievement.unlocked ? <Icon className="size-6" /> : <Lock className="size-5" />}
                    </span>
                    <Badge variant={TIER_VARIANTS[achievement.tier] || 'secondary'}>
                      {achievement.tier}
                    </Badge>
                  </div>

                  <h3 className="mt-3 font-display text-base font-semibold">{achievement.name}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">{achievement.description}</p>

                  <div className="mt-4">
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>
                        {Math.min(achievement.current_value, achievement.target_value)}/
                        {achievement.target_value}
                      </span>
                      <span>+{achievement.xp_reward} XP</span>
                    </div>
                    <Progress value={achievement.progress} className="mt-1.5 h-1.5" />
                  </div>

                  {achievement.unlocked && achievement.unlocked_at && (
                    <p className="mt-3 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                      Unlocked {new Date(achievement.unlocked_at).toLocaleDateString('en-GB', {
                        day: 'numeric',
                        month: 'short',
                        year: 'numeric',
                      })}
                    </p>
                  )}
                </Card>
              </motion.div>
            )
          })}
        </div>
      )}
    </div>
  )
}

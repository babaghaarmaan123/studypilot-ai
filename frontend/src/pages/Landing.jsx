import { useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Award,
  BarChart3,
  BookOpen,
  CalendarClock,
  ChevronDown,
  GraduationCap,
  Menu,
  Moon,
  Rocket,
  Sparkles,
  Sun,
  Target,
  Wand2,
  X,
} from 'lucide-react'

import { useTheme } from '@/context/ThemeContext'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const NAV_LINKS = [
  { href: '#features', label: 'Features' },
  { href: '#testimonials', label: 'Testimonials' },
  { href: '#faq', label: 'FAQ' },
]

const FEATURES = [
  {
    icon: Wand2,
    title: 'AI Study Planner',
    description:
      'A personalised day-by-day timetable built from your exam dates, subject difficulty, available hours and remaining syllabus.',
    tone: 'bg-primary/10 text-primary',
  },
  {
    icon: BookOpen,
    title: 'Revision Planner',
    description:
      'Spaced-repetition checkpoints at 2, 7 and 14 days after every topic, plus a final pass before each exam.',
    tone: 'from-emerald-500/15 to-teal-500/10 text-emerald-600 dark:text-emerald-300',
  },
  {
    icon: CalendarClock,
    title: 'Exam Countdown',
    description:
      'Live countdowns for every school and admissions exam, with a readiness score that updates as you study.',
    tone: 'from-amber-500/15 to-orange-500/10 text-amber-600 dark:text-amber-300',
  },
  {
    icon: BarChart3,
    title: 'Analytics',
    description:
      'Weekly and monthly hours, subject split, streaks and past-paper improvement in one place.',
    tone: 'from-sky-500/15 to-cyan-500/10 text-sky-600 dark:text-sky-300',
  },
  {
    icon: GraduationCap,
    title: 'University Admission Preparation',
    description:
      'TMUA, ESAT, MAT, PAT, STEP, LNAT, UCAT, Oxford and Cambridge tests, IELTS and PTE, built into your weekly plan.',
    tone: 'bg-primary/10 text-primary',
  },
  {
    icon: Award,
    title: 'Achievements & Streaks',
    description:
      'XP, levels and badges for daily streaks, perfect weeks and syllabus milestones.',
    tone: 'from-rose-500/15 to-pink-500/10 text-rose-600 dark:text-rose-300',
  },
]

const TESTIMONIALS = [
  {
    name: 'Amara O.',
    role: 'Year 13 · A Levels · Applying to Cambridge (Engineering)',
    quote:
      'StudyPilot worked out exactly how to split my week between Further Maths revision and STEP practice. I stopped guessing what to do each evening.',
  },
  {
    name: 'Rohan K.',
    role: 'Year 11 · GCSE',
    quote:
      'The exam countdown made revision feel manageable instead of terrifying. Marking topics off and watching the streak grow actually kept me consistent.',
  },
  {
    name: 'Sofia M.',
    role: 'Year 13 · International A Levels · Applying to Imperial (Medicine)',
    quote:
      'Having UCAT practice automatically scheduled alongside my Biology and Chemistry syllabus meant I never had to plan admissions prep separately.',
  },
]

const FAQS = [
  {
    q: 'Which students is StudyPilot AI for?',
    a: 'StudyPilot is built specifically for GCSE, A Level and International A Level students. It does not currently support undergraduate, postgraduate, Foundation Programme or IB Diploma study.',
  },
  {
    q: 'How does the AI study planner actually work?',
    a: 'It scores every subject on exam proximity, difficulty, priority and remaining syllabus, then fills your available hours block by block. Miss a session and it reshuffles.',
  },
  {
    q: 'What is spaced-repetition revision?',
    a: 'Whenever you complete a topic, StudyPilot books recall checkpoints 2, 7 and 14 days later, plus a final pass a few days before the exam.',
  },
  {
    q: 'Can I prepare for university admissions tests too?',
    a: 'Yes. Tell us which tests you are sitting (TMUA, ESAT, MAT, PAT, STEP, LNAT, UCAT, Oxford and Cambridge tests, IELTS or PTE) during onboarding, and practice sessions are added to your weekly plan.',
  },
  {
    q: 'Is my data private?',
    a: 'Your study data belongs to you. Passwords are hashed, sessions use JWT authentication, and you can export or delete your account and all associated data at any time from Settings.',
  },
]

function ThemeToggleFloating() {
  const { isDark, toggleTheme } = useTheme()
  return (
    <Button variant="ghost" size="icon" onClick={toggleTheme} aria-label="Toggle dark mode">
      {isDark ? <Sun className="size-4.5" /> : <Moon className="size-4.5" />}
    </Button>
  )
}

function FaqItem({ item, index }) {
  const [open, setOpen] = useState(index === 0)
  return (
    <div className="rounded-2xl border border-border/70 bg-card shadow-soft">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left"
        aria-expanded={open}
      >
        <span className="font-display text-sm font-semibold sm:text-base">{item.q}</span>
        <ChevronDown
          className={cn('size-4.5 shrink-0 text-muted-foreground transition-transform', open && 'rotate-180')}
        />
      </button>
      {open && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="overflow-hidden px-5 pb-4 text-sm text-muted-foreground"
        >
          {item.a}
        </motion.div>
      )}
    </div>
  )
}

export default function Landing() {
  const [navOpen, setNavOpen] = useState(false)

  return (
    <div className="relative min-h-screen overflow-x-clip bg-background">
      <div className="pastel-mesh pointer-events-none absolute inset-x-0 top-0 -z-10 h-[640px]" aria-hidden="true" />

      {/* Nav */}
      <header className="sticky top-0 z-40 border-b border-border/60 bg-background/75 backdrop-blur-xl">
        <div className="container flex h-16 items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5">
            <span className="grid size-9 place-items-center rounded-xl bg-primary text-primary-foreground">
              <Rocket className="size-4.5" />
            </span>
            <span className="font-display text-lg font-bold tracking-tight">
              StudyPilot <span className="text-gradient">AI</span>
            </span>
          </Link>

          <nav className="hidden items-center gap-7 md:flex">
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
              >
                {link.label}
              </a>
            ))}
          </nav>

          <div className="hidden items-center gap-2 md:flex">
            <ThemeToggleFloating />
            <Button variant="ghost" asChild>
              <Link to="/login">Login</Link>
            </Button>
            <Button asChild>
              <Link to="/register">
                Get Started <Sparkles />
              </Link>
            </Button>
          </div>

          <button
            className="grid size-10 place-items-center rounded-xl text-foreground md:hidden"
            onClick={() => setNavOpen((v) => !v)}
            aria-label="Toggle menu"
          >
            {navOpen ? <X className="size-5" /> : <Menu className="size-5" />}
          </button>
        </div>

        {navOpen && (
          <div className="border-t border-border/60 px-4 py-4 md:hidden">
            <nav className="flex flex-col gap-3">
              {NAV_LINKS.map((link) => (
                <a
                  key={link.href}
                  href={link.href}
                  onClick={() => setNavOpen(false)}
                  className="text-sm font-medium text-muted-foreground"
                >
                  {link.label}
                </a>
              ))}
            </nav>
            <div className="mt-4 flex items-center gap-2">
              <Button variant="outline" className="flex-1" asChild>
                <Link to="/login">Login</Link>
              </Button>
              <Button className="flex-1" asChild>
                <Link to="/register">Get Started</Link>
              </Button>
              <ThemeToggleFloating />
            </div>
          </div>
        )}
      </header>

      {/* Hero */}
      <section className="container flex flex-col items-center gap-8 py-20 text-center sm:py-28">
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3.5 py-1.5 text-xs font-semibold text-muted-foreground shadow-soft">
            <Sparkles className="size-3.5 text-primary" />
            Built for GCSE · A Level · International A Level
          </span>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.05 }}
          className="max-w-3xl font-display text-4xl font-bold leading-[1.1] tracking-tight sm:text-6xl"
        >
          Study Smarter.{' '}
          <span className="text-gradient">Achieve More.</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.1 }}
          className="max-w-xl text-balance text-base text-muted-foreground sm:text-lg"
        >
          Your AI-powered study companion designed specifically for GCSE, A Level and
          International A Level students.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.15 }}
          className="flex flex-col gap-3 sm:flex-row"
        >
          <Button size="lg" asChild>
            <Link to="/register">
              Get Started <Sparkles />
            </Link>
          </Button>
          <Button size="lg" variant="outline" asChild>
            <Link to="/login">Login</Link>
          </Button>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.25 }}
          className="mt-6 grid w-full max-w-3xl grid-cols-2 gap-3 sm:grid-cols-4"
        >
          {[
            ['3', 'Curricula supported'],
            ['11', 'Admissions tests'],
            ['2·7·14', 'Day revision ladder'],
            ['24/7', 'AI-generated plans'],
          ].map(([value, label]) => (
            <div
              key={label}
              className="rounded-2xl border border-border/70 bg-card/80 p-4 shadow-soft backdrop-blur"
            >
              <p className="font-display text-2xl font-bold text-primary">{value}</p>
              <p className="mt-0.5 text-xs text-muted-foreground">{label}</p>
            </div>
          ))}
        </motion.div>
      </section>

      {/* Features */}
      <section id="features" className="container py-16 sm:py-24">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">
            Everything your revision needs, in one place
          </h2>
          <p className="mt-3 text-muted-foreground">
            StudyPilot turns your exam timetable and syllabus into a plan you can actually follow.
          </p>
        </div>

        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-60px' }}
              transition={{ duration: 0.4, delay: (index % 3) * 0.08 }}
              className="card-hover rounded-2xl border border-border/70 bg-card p-6 shadow-card"
            >
              <span
                className={cn(
                  'grid size-12 place-items-center rounded-2xl bg-gradient-to-br',
                  feature.tone,
                )}
              >
                <feature.icon className="size-6" />
              </span>
              <h3 className="mt-4 font-display text-lg font-semibold">{feature.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                {feature.description}
              </p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="border-y border-border/60 bg-muted/40 py-16 sm:py-24">
        <div className="container">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">
              From signup to your first plan in minutes
            </h2>
          </div>
          <div className="mt-12 grid gap-6 sm:grid-cols-3">
            {[
              {
                step: '01',
                title: 'Tell your AI Study Mentor about you',
                body: 'A short 10-question onboarding covers your year group, subjects, exams, admissions tests and study habits.',
              },
              {
                step: '02',
                title: 'Get your personalised plan',
                body: 'StudyPilot generates a 28-day timetable balancing school revision with admissions preparation.',
              },
              {
                step: '03',
                title: 'Study, track and adapt',
                body: 'Complete sessions, log past papers and watch your plan automatically adjust to keep you on target.',
              },
            ].map((item) => (
              <div key={item.step} className="rounded-2xl border border-border/70 bg-card p-6 shadow-soft">
                <span className="font-display text-3xl font-bold text-primary/30">{item.step}</span>
                <h3 className="mt-3 font-display text-base font-semibold">{item.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{item.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section id="testimonials" className="container py-16 sm:py-24">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">
            Students are hitting their targets
          </h2>
        </div>
        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {TESTIMONIALS.map((t, index) => (
            <motion.figure
              key={t.name}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-60px' }}
              transition={{ duration: 0.4, delay: index * 0.08 }}
              className="flex h-full flex-col justify-between rounded-2xl border border-border/70 bg-card p-6 shadow-card"
            >
              <blockquote className="text-sm leading-relaxed text-foreground/90">
                “{t.quote}”
              </blockquote>
              <figcaption className="mt-5 border-t border-border/60 pt-4">
                <p className="text-sm font-semibold">{t.name}</p>
                <p className="text-xs text-muted-foreground">{t.role}</p>
              </figcaption>
            </motion.figure>
          ))}
        </div>
      </section>

      {/* FAQ */}
      <section id="faq" className="border-t border-border/60 bg-muted/40 py-16 sm:py-24">
        <div className="container">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">
              Frequently asked questions
            </h2>
          </div>
          <div className="mx-auto mt-10 max-w-2xl space-y-3">
            {FAQS.map((item, index) => (
              <FaqItem key={item.q} item={item} index={index} />
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="container py-16 sm:py-24">
        <div className="relative overflow-hidden rounded-4xl border border-border/70 bg-primary px-6 py-14 text-center text-primary-foreground shadow-lift sm:px-12">
          <Target className="mx-auto size-10 opacity-80" />
          <h2 className="mt-4 font-display text-3xl font-bold tracking-tight sm:text-4xl">
            Ready to build your personalised study plan?
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-white/85">
            Join students preparing for GCSE, A Level and International A Level
            exams, and university admissions, with a plan built around their real
            timetable.
          </p>
          <Button size="lg" variant="secondary" className="mt-7 text-indigo-700" asChild>
            <Link to="/register">
              Get Started Free <Sparkles />
            </Link>
          </Button>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/60 py-10">
        <div className="container flex flex-col items-center justify-between gap-6 sm:flex-row">
          <div className="flex items-center gap-2.5">
            <span className="grid size-8 place-items-center rounded-lg bg-primary text-primary-foreground">
              <Rocket className="size-4" />
            </span>
            <span className="font-display text-sm font-bold">StudyPilot AI</span>
          </div>
          <p className="text-center text-xs text-muted-foreground">
            © {new Date().getFullYear()} StudyPilot AI. Built for GCSE, A Level and
            International A Level students only.
          </p>
          <div className="flex items-center gap-5 text-xs text-muted-foreground">
            <a href="#features" className="hover:text-foreground">Features</a>
            <a href="#faq" className="hover:text-foreground">FAQ</a>
            <Link to="/login" className="hover:text-foreground">Login</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}

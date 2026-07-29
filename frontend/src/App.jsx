import { Suspense, lazy } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { Loader2 } from 'lucide-react'

import { useAuth } from '@/context/AuthContext'
import AppShell from '@/components/layout/AppShell'

// The landing and auth screens are what a first-time visitor waits for, so
// they stay in the entry bundle. Everything behind the sign-in wall is split
// out and fetched on navigation — that keeps the initial download small and
// stops the charts and PDF libraries loading for someone who is only signing in.
import Landing from '@/pages/Landing'
import Login from '@/pages/auth/Login'
import Register from '@/pages/auth/Register'

const ForgotPassword = lazy(() => import('@/pages/auth/ForgotPassword'))
const ResetPassword = lazy(() => import('@/pages/auth/ResetPassword'))
const Onboarding = lazy(() => import('@/pages/onboarding/Onboarding'))
const Dashboard = lazy(() => import('@/pages/Dashboard'))
const StudyPlanner = lazy(() => import('@/pages/StudyPlanner'))
const Subjects = lazy(() => import('@/pages/Subjects'))
const SubjectDetail = lazy(() => import('@/pages/SubjectDetail'))
const Syllabus = lazy(() => import('@/pages/Syllabus'))
const CalendarPage = lazy(() => import('@/pages/Calendar'))
const Revision = lazy(() => import('@/pages/Revision'))
const PastPapers = lazy(() => import('@/pages/PastPapers'))
const Analytics = lazy(() => import('@/pages/Analytics'))
const Achievements = lazy(() => import('@/pages/Achievements'))
const Profile = lazy(() => import('@/pages/Profile'))
const Settings = lazy(() => import('@/pages/Settings'))
const NotFound = lazy(() => import('@/pages/NotFound'))

function FullscreenLoader() {
  return (
    <div className="grid min-h-screen place-items-center bg-background">
      <div className="flex flex-col items-center gap-3 text-muted-foreground">
        <Loader2 className="size-8 animate-spin text-primary" />
        <p className="text-sm font-medium">Loading StudyPilot…</p>
      </div>
    </div>
  )
}

function RequireAuth({ children }) {
  const { isAuthenticated, loading, needsOnboarding } = useAuth()
  const location = useLocation()
  if (loading) return <FullscreenLoader />
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location }} replace />
  if (needsOnboarding) return <Navigate to="/onboarding" replace />
  return children
}

function RequireOnboardingAccess({ children }) {
  const { isAuthenticated, loading, needsOnboarding } = useAuth()
  if (loading) return <FullscreenLoader />
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (!needsOnboarding) return <Navigate to="/dashboard" replace />
  return children
}

function RedirectIfAuthed({ children }) {
  const { isAuthenticated, loading, needsOnboarding } = useAuth()
  if (loading) return <FullscreenLoader />
  if (isAuthenticated) {
    return <Navigate to={needsOnboarding ? '/onboarding' : '/dashboard'} replace />
  }
  return children
}

export default function App() {
  return (
    // One boundary around the whole route tree: a lazily loaded page shows the
    // same fullscreen loader the auth bootstrap already uses.
    <Suspense fallback={<FullscreenLoader />}>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route
          path="/login"
          element={
            <RedirectIfAuthed>
              <Login />
            </RedirectIfAuthed>
          }
        />
        <Route
          path="/register"
          element={
            <RedirectIfAuthed>
              <Register />
            </RedirectIfAuthed>
          }
        />
        <Route
          path="/forgot-password"
          element={
            <RedirectIfAuthed>
              <ForgotPassword />
            </RedirectIfAuthed>
          }
        />
        <Route path="/reset-password" element={<ResetPassword />} />

        <Route
          path="/onboarding"
          element={
            <RequireOnboardingAccess>
              <Onboarding />
            </RequireOnboardingAccess>
          }
        />

        <Route
          element={
            <RequireAuth>
              <AppShell />
            </RequireAuth>
          }
        >
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/planner" element={<StudyPlanner />} />
          <Route path="/subjects" element={<Subjects />} />
          <Route path="/subjects/:id" element={<SubjectDetail />} />
          <Route path="/syllabus" element={<Syllabus />} />
          <Route path="/syllabus/:subjectId" element={<Syllabus />} />
          <Route path="/calendar" element={<CalendarPage />} />
          <Route path="/revision" element={<Revision />} />
          <Route path="/past-papers" element={<PastPapers />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/achievements" element={<Achievements />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/settings" element={<Settings />} />
        </Route>

        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  )
}

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Compass } from 'lucide-react';
import { createBrowserRouter, Link, Navigate, Outlet, RouterProvider, useLocation } from 'react-router-dom';
import { ApiError } from '@/api/client';
import { useMe } from '@/api/queries';
import { EmptyState } from '@/components/ui/EmptyState';
import { LogoMark } from '@/components/ui/Logo';
import { Toaster } from '@/components/ui/Toaster';
import { TooltipProvider } from '@/components/ui/Tooltip';
import { LoginPage } from '@/features/auth/LoginPage';
import { ChatPage } from '@/features/chat/ChatPage';
import { NewChatPage } from '@/features/chat/NewChatPage';
import { AppShell } from '@/features/layout/AppShell';
import { DocumentPage } from '@/features/library/DocumentPage';
import { LibraryPage } from '@/features/library/LibraryPage';
import { SettingsPage } from '@/features/settings/SettingsPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      retry: (count, err) => !(err instanceof ApiError && err.status < 500) && count < 2,
    },
  },
});

function RequireAuth() {
  const { data: me, isLoading } = useMe();
  const location = useLocation();
  if (isLoading) {
    return (
      <div className="flex h-dvh items-center justify-center bg-bg" aria-busy aria-label="Loading">
        <LogoMark className="size-10 animate-pulse" />
      </div>
    );
  }
  if (!me) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return <Outlet />;
}

function NotFound() {
  return (
    <div className="flex flex-1 items-center justify-center">
      <EmptyState icon={<Compass />} title="Page not found" action={<Link to="/" className="text-sm font-medium text-primary hover:underline">Go to a new chat</Link>}>
        The page you’re looking for doesn’t exist.
      </EmptyState>
    </div>
  );
}

const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppShell />,
        children: [
          { index: true, element: <NewChatPage /> },
          { path: 'c/:conversationId', element: <ChatPage /> },
          { path: 'library', element: <LibraryPage /> },
          { path: 'library/:documentId', element: <DocumentPage /> },
          { path: 'settings', element: <SettingsPage /> },
          { path: '*', element: <NotFound /> },
        ],
      },
    ],
  },
]);

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider delayDuration={350} skipDelayDuration={150}>
        <RouterProvider router={router} />
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

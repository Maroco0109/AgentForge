import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '../auth-context';

const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}));

// Helper component to expose auth context values
function AuthConsumer() {
  const { user, token, isLoading, login, logout, register } = useAuth();
  return (
    <div>
      <span data-testid="user">{user?.email ?? 'no-user'}</span>
      <span data-testid="token">{token ?? 'no-token'}</span>
      <span data-testid="loading">{isLoading ? 'loading' : 'ready'}</span>
      <button onClick={() => login('test@example.com', 'pass123')}>Login</button>
      <button onClick={() => logout()}>Logout</button>
      <button onClick={() => register('reg@example.com', 'pass123', 'reguser')}>Register</button>
    </div>
  );
}

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    global.fetch = vi.fn();
  });

  it('login stores token and user in localStorage', async () => {
    // Create a minimal valid JWT: header.payload.signature (base64)
    const payload = btoa(JSON.stringify({ sub: 'test@example.com', display_name: 'Tester' }));
    const fakeToken = `header.${payload}.sig`;

    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ access_token: fakeToken }),
    });

    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>
    );

    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('ready'));

    await act(async () => {
      screen.getByRole('button', { name: 'Login' }).click();
    });

    await waitFor(() => {
      expect(localStorage.getItem('access_token')).toBe(fakeToken);
      expect(screen.getByTestId('user')).toHaveTextContent('test@example.com');
    });
  });

  it('logout clears localStorage and user state', async () => {
    localStorage.setItem('access_token', 'some-token');

    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>
    );

    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('ready'));

    act(() => {
      screen.getByRole('button', { name: 'Logout' }).click();
    });

    await waitFor(() => {
      expect(localStorage.getItem('access_token')).toBeNull();
      expect(screen.getByTestId('user')).toHaveTextContent('no-user');
      expect(screen.getByTestId('token')).toHaveTextContent('no-token');
    });
  });

  it('register calls API and redirects to login', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    });

    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>
    );

    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('ready'));

    await act(async () => {
      screen.getByRole('button', { name: 'Register' }).click();
    });

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/login');
    });
  });

  it('provides auth state to children', async () => {
    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>
    );

    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('ready'));

    expect(screen.getByTestId('user')).toBeInTheDocument();
    expect(screen.getByTestId('token')).toBeInTheDocument();
  });
});

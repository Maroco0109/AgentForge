import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import RegisterPage from '../page';

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

// Mock auth context
const mockRegister = vi.fn();
vi.mock('@/lib/auth-context', () => ({
  useAuth: () => ({
    register: mockRegister,
    login: vi.fn(),
    logout: vi.fn(),
    user: null,
    token: null,
    isLoading: false,
  }),
}));

// Mock next/link
vi.mock('next/link', () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

describe('RegisterPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders registration form with username, email, and password fields', () => {
    render(<RegisterPage />);
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /register/i })).toBeInTheDocument();
  });

  it('submits form with user data', async () => {
    mockRegister.mockResolvedValueOnce(undefined);
    render(<RegisterPage />);

    fireEvent.change(screen.getByLabelText(/username/i), {
      target: { value: 'johndoe' },
    });
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: 'john@example.com' },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'password123' },
    });
    fireEvent.submit(screen.getByRole('button', { name: /register/i }).closest('form')!);

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith('john@example.com', 'password123', 'johndoe');
    });
  });

  it('shows error message on failed registration', async () => {
    mockRegister.mockRejectedValueOnce(new Error('Email already exists'));
    render(<RegisterPage />);

    fireEvent.submit(screen.getByRole('button', { name: /register/i }).closest('form')!);

    await waitFor(() => {
      expect(screen.getByText('Email already exists')).toBeInTheDocument();
    });
  });

  it('has link to login page', () => {
    render(<RegisterPage />);
    const loginLink = screen.getByRole('link', { name: /login/i });
    expect(loginLink).toBeInTheDocument();
    expect(loginLink).toHaveAttribute('href', '/login');
  });
});

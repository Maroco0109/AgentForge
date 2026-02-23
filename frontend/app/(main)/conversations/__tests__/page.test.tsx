import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ConversationsPage from '../page';

const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}));

vi.mock('@/lib/api', () => ({
  apiFetch: vi.fn(),
}));

import { apiFetch } from '@/lib/api';
const mockApiFetch = apiFetch as ReturnType<typeof vi.fn>;

describe('ConversationsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders conversation list when conversations exist', async () => {
    mockApiFetch.mockResolvedValueOnce([
      { id: '1', title: 'First Conversation', created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
      { id: '2', title: 'Second Conversation', created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
    ]);

    render(<ConversationsPage />);

    await waitFor(() => {
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
      expect(screen.getByText('Second Conversation')).toBeInTheDocument();
    });
  });

  it('shows empty state when no conversations', async () => {
    mockApiFetch.mockResolvedValueOnce([]);

    render(<ConversationsPage />);

    await waitFor(() => {
      expect(screen.getByText('No conversations yet')).toBeInTheDocument();
    });
  });

  it('has "New Conversation" button in header', async () => {
    mockApiFetch.mockResolvedValueOnce([]);

    render(<ConversationsPage />);

    // The header button is always visible
    const buttons = await screen.findAllByRole('button', { name: /new conversation/i });
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('handles API error gracefully', async () => {
    mockApiFetch.mockRejectedValueOnce(new Error('Network error'));

    render(<ConversationsPage />);

    // Should not crash and should show empty state or the header
    await waitFor(() => {
      expect(screen.getByText('Conversations')).toBeInTheDocument();
    });
  });

  it('navigates to conversation on click', async () => {
    mockApiFetch.mockResolvedValueOnce([
      { id: 'abc123', title: 'My Chat', created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
    ]);

    render(<ConversationsPage />);

    await waitFor(() => {
      expect(screen.getByText('My Chat')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('My Chat'));
    expect(mockPush).toHaveBeenCalledWith('/chat/abc123');
  });
});

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import TemplatesPage from '../page';

const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}));

vi.mock('@/lib/api', () => ({
  apiFetch: vi.fn(),
}));

import { apiFetch } from '@/lib/api';
const mockApiFetch = apiFetch as ReturnType<typeof vi.fn>;

const sampleTemplates = [
  { id: '1', name: 'Alpha Template', description: 'First template description', is_public: true, created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
  { id: '2', name: 'Beta Template', description: 'Second template description', is_public: false, created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
];

describe('TemplatesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders template list when templates exist', async () => {
    mockApiFetch.mockResolvedValueOnce(sampleTemplates);

    render(<TemplatesPage />);

    await waitFor(() => {
      expect(screen.getByText('Alpha Template')).toBeInTheDocument();
      expect(screen.getByText('Beta Template')).toBeInTheDocument();
    });
  });

  it('shows empty state when no templates exist', async () => {
    mockApiFetch.mockResolvedValueOnce([]);

    render(<TemplatesPage />);

    await waitFor(() => {
      expect(screen.getByText(/no templates yet/i)).toBeInTheDocument();
    });
  });

  it('filters templates by search query', async () => {
    mockApiFetch.mockResolvedValueOnce(sampleTemplates);

    render(<TemplatesPage />);

    await waitFor(() => {
      expect(screen.getByText('Alpha Template')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/search templates/i);
    fireEvent.change(searchInput, { target: { value: 'Alpha' } });

    expect(screen.getByText('Alpha Template')).toBeInTheDocument();
    expect(screen.queryByText('Beta Template')).not.toBeInTheDocument();
  });

  it('handles API error and shows retry button', async () => {
    mockApiFetch.mockRejectedValueOnce(new Error('Server error'));

    render(<TemplatesPage />);

    await waitFor(() => {
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });
  });

  it('shows template cards with name and description', async () => {
    mockApiFetch.mockResolvedValueOnce(sampleTemplates);

    render(<TemplatesPage />);

    await waitFor(() => {
      expect(screen.getByText('Alpha Template')).toBeInTheDocument();
      expect(screen.getByText('First template description')).toBeInTheDocument();
    });
  });

  it('navigates to template detail on click', async () => {
    mockApiFetch.mockResolvedValueOnce(sampleTemplates);

    render(<TemplatesPage />);

    await waitFor(() => {
      expect(screen.getByText('Alpha Template')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Alpha Template'));
    expect(mockPush).toHaveBeenCalledWith('/templates/1');
  });
});

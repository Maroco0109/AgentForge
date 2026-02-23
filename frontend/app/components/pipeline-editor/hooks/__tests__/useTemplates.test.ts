import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useTemplates } from '../useTemplates';

vi.mock('@/lib/api', () => ({
  apiFetch: vi.fn(),
}));

import { apiFetch } from '@/lib/api';
const mockApiFetch = apiFetch as ReturnType<typeof vi.fn>;

const sampleTemplates = [
  { id: '1', name: 'Template A', description: null, is_public: false, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
];

describe('useTemplates', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('fetches templates on explicit fetchTemplates call', async () => {
    mockApiFetch.mockResolvedValueOnce(sampleTemplates);

    const { result } = renderHook(() => useTemplates());

    await act(async () => {
      await result.current.fetchTemplates();
    });

    expect(result.current.templates).toEqual(sampleTemplates);
    expect(mockApiFetch).toHaveBeenCalledWith('/api/v1/templates');
  });

  it('respects cache TTL: does not re-fetch within 30 seconds', async () => {
    mockApiFetch.mockResolvedValue(sampleTemplates);

    const { result } = renderHook(() => useTemplates());

    // First fetch
    await act(async () => {
      await result.current.fetchTemplates();
    });

    // Advance time by 10 seconds (within TTL)
    vi.advanceTimersByTime(10000);

    // Second call - should use cache
    await act(async () => {
      await result.current.fetchTemplates();
    });

    expect(mockApiFetch).toHaveBeenCalledTimes(1);
  });

  it('force refresh bypasses cache', async () => {
    mockApiFetch.mockResolvedValue(sampleTemplates);

    const { result } = renderHook(() => useTemplates());

    // First fetch
    await act(async () => {
      await result.current.fetchTemplates();
    });

    // Force refresh within TTL
    await act(async () => {
      await result.current.fetchTemplates(true);
    });

    expect(mockApiFetch).toHaveBeenCalledTimes(2);
  });

  it('saveTemplate calls apiFetch with POST and then refreshes', async () => {
    // First call: save, second call: refresh
    mockApiFetch
      .mockResolvedValueOnce(undefined)    // POST save
      .mockResolvedValueOnce(sampleTemplates); // GET refresh

    const { result } = renderHook(() => useTemplates());

    await act(async () => {
      await result.current.saveTemplate({
        name: 'New Template',
        description: 'desc',
        graph_data: {},
        design_data: {},
      });
    });

    expect(mockApiFetch).toHaveBeenCalledWith('/api/v1/templates', expect.objectContaining({ method: 'POST' }));
    expect(result.current.templates).toEqual(sampleTemplates);
  });

  it('deleteTemplate calls apiFetch with DELETE and then refreshes', async () => {
    mockApiFetch
      .mockResolvedValueOnce(undefined)   // DELETE
      .mockResolvedValueOnce([]);          // GET refresh

    const { result } = renderHook(() => useTemplates());

    await act(async () => {
      await result.current.deleteTemplate('1');
    });

    expect(mockApiFetch).toHaveBeenCalledWith('/api/v1/templates/1', { method: 'DELETE' });
    expect(result.current.templates).toEqual([]);
  });
});

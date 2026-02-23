import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { apiFetch } from '../api';

describe('apiFetch', () => {
  const originalFetch = global.fetch;
  const originalLocation = window.location;

  beforeEach(() => {
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null);
    vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {});
    global.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    global.fetch = originalFetch;
  });

  it('returns parsed JSON on successful GET request (200)', async () => {
    const mockData = { id: '1', name: 'Test' };
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockData,
    });

    const result = await apiFetch<typeof mockData>('/api/v1/test');
    expect(result).toEqual(mockData);
  });

  it('handles 401 unauthorized: clears token and redirects', async () => {
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue('old-token');
    const removeItemSpy = vi.spyOn(Storage.prototype, 'removeItem');
    // jsdom allows assignment to window.location.href
    delete (window as unknown as { location?: unknown }).location;
    (window as unknown as { location: { href: string } }).location = { href: '' };

    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Unauthorized' }),
      statusText: 'Unauthorized',
    });

    const result = await apiFetch<null>('/api/v1/protected');
    expect(removeItemSpy).toHaveBeenCalledWith('access_token');
    expect((window as unknown as { location: { href: string } }).location.href).toBe('/login');
    expect(result).toBeUndefined();
  });

  it('handles 422 validation error with array detail', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 422,
      statusText: 'Unprocessable Entity',
      json: async () => ({ detail: [{ msg: 'field required' }, { msg: 'invalid email' }] }),
    });

    await expect(apiFetch('/api/v1/test')).rejects.toThrow('field required, invalid email');
  });

  it('handles 204 no content and returns undefined', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      status: 204,
      json: async () => { throw new Error('no body'); },
    });

    const result = await apiFetch<void>('/api/v1/test');
    expect(result).toBeUndefined();
  });

  it('handles network error (fetch throws)', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('Network Error'));

    await expect(apiFetch('/api/v1/test')).rejects.toThrow('Network Error');
  });

  it('sends Authorization header when token exists in localStorage', async () => {
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue('my-jwt-token');
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({}),
    });

    await apiFetch('/api/v1/test');

    const callArgs = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const headers = callArgs[1].headers;
    expect(headers['Authorization']).toBe('Bearer my-jwt-token');
  });

  it('does not send Authorization header when no token in localStorage', async () => {
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null);
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({}),
    });

    await apiFetch('/api/v1/test');

    const callArgs = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const headers = callArgs[1].headers;
    expect(headers['Authorization']).toBeUndefined();
  });

  it('handles non-array string detail error gracefully', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 400,
      statusText: 'Bad Request',
      json: async () => ({ detail: 'Something went wrong' }),
    });

    await expect(apiFetch('/api/v1/test')).rejects.toThrow('Something went wrong');
  });
});

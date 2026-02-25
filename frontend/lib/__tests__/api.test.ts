import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock auth module BEFORE importing api
vi.mock("../auth", () => ({
  getAccessToken: vi.fn(() => null),
  getRefreshTokenFromStorage: vi.fn(() => null),
  refreshToken: vi.fn(),
  saveTokens: vi.fn(),
  clearTokens: vi.fn(),
}));

import { apiFetch, _resetRefreshState } from "../api";
import * as authModule from "../auth";

describe("apiFetch", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.clearAllMocks();
    _resetRefreshState();
    global.fetch = vi.fn();
    vi.mocked(authModule.getAccessToken).mockReturnValue(null);
    vi.mocked(authModule.getRefreshTokenFromStorage).mockReturnValue(null);
    // Reset window.location
    delete (window as unknown as { location?: unknown }).location;
    (window as unknown as { location: { href: string } }).location = {
      href: "",
    };
  });

  afterEach(() => {
    vi.restoreAllMocks();
    global.fetch = originalFetch;
  });

  it("returns parsed JSON on successful GET request (200)", async () => {
    const mockData = { id: "1", name: "Test" };
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockData,
    });

    const result = await apiFetch<typeof mockData>("/api/v1/test");
    expect(result).toEqual(mockData);
  });

  it("handles 204 no content and returns undefined", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      status: 204,
      json: async () => {
        throw new Error("no body");
      },
    });

    const result = await apiFetch<void>("/api/v1/test");
    expect(result).toBeUndefined();
  });

  it("handles network error (fetch throws)", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new Error("Network Error")
    );
    await expect(apiFetch("/api/v1/test")).rejects.toThrow("Network Error");
  });

  it("sends Authorization header when token exists", async () => {
    vi.mocked(authModule.getAccessToken).mockReturnValue("my-jwt-token");
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({}),
    });

    await apiFetch("/api/v1/test");

    const callArgs = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const headers = callArgs[1].headers;
    expect(headers["Authorization"]).toBe("Bearer my-jwt-token");
  });

  it("does not send Authorization header when no token", async () => {
    vi.mocked(authModule.getAccessToken).mockReturnValue(null);
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({}),
    });

    await apiFetch("/api/v1/test");

    const callArgs = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const headers = callArgs[1].headers;
    expect(headers["Authorization"]).toBeUndefined();
  });

  it("handles 422 validation error with array detail", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 422,
      statusText: "Unprocessable Entity",
      json: async () => ({
        detail: [{ msg: "field required" }, { msg: "invalid email" }],
      }),
    });

    await expect(apiFetch("/api/v1/test")).rejects.toThrow(
      "field required, invalid email"
    );
  });

  it("handles non-array string detail error gracefully", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 400,
      statusText: "Bad Request",
      json: async () => ({ detail: "Something went wrong" }),
    });

    await expect(apiFetch("/api/v1/test")).rejects.toThrow(
      "Something went wrong"
    );
  });

  // Token Refresh Tests
  describe("token refresh on 401", () => {
    it("redirects to login when no refresh token available", async () => {
      vi.mocked(authModule.getRefreshTokenFromStorage).mockReturnValue(null);
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: "Unauthorized",
        json: async () => ({ detail: "Unauthorized" }),
      });

      await apiFetch("/api/v1/protected");
      expect(authModule.clearTokens).toHaveBeenCalled();
      expect(window.location.href).toBe("/login");
    });

    it("refreshes token and retries on 401", async () => {
      vi.mocked(authModule.getRefreshTokenFromStorage).mockReturnValue(
        "valid-refresh"
      );
      vi.mocked(authModule.refreshToken).mockResolvedValueOnce({
        access_token: "new-access",
        refresh_token: "new-refresh",
        token_type: "bearer",
      });
      vi.mocked(authModule.getAccessToken)
        .mockReturnValueOnce("old-token")
        .mockReturnValueOnce("new-access");

      const mockData = { id: "1" };
      (global.fetch as ReturnType<typeof vi.fn>)
        .mockResolvedValueOnce({
          ok: false,
          status: 401,
          statusText: "Unauthorized",
          json: async () => ({ detail: "Token expired" }),
        })
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => mockData,
        });

      const result = await apiFetch("/api/v1/protected");
      expect(authModule.refreshToken).toHaveBeenCalledWith("valid-refresh");
      expect(authModule.saveTokens).toHaveBeenCalled();
      expect(result).toEqual(mockData);
    });

    it("does not retry refresh on /auth/refresh endpoint (infinite loop prevention)", async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: "Unauthorized",
        json: async () => ({ detail: "Unauthorized" }),
      });

      await apiFetch("/api/v1/auth/refresh");
      expect(authModule.clearTokens).toHaveBeenCalled();
      expect(window.location.href).toBe("/login");
      expect(authModule.refreshToken).not.toHaveBeenCalled();
    });

    it("logs out when refresh fails", async () => {
      vi.mocked(authModule.getRefreshTokenFromStorage).mockReturnValue(
        "expired-refresh"
      );
      vi.mocked(authModule.refreshToken).mockRejectedValueOnce(
        new Error("Refresh failed")
      );

      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: "Unauthorized",
        json: async () => ({ detail: "Token expired" }),
      });

      await apiFetch("/api/v1/protected");
      expect(authModule.clearTokens).toHaveBeenCalled();
      expect(window.location.href).toBe("/login");
    });

    it("handles concurrent 401s with single refresh (mutex)", async () => {
      vi.mocked(authModule.getRefreshTokenFromStorage).mockReturnValue(
        "valid-refresh"
      );
      vi.mocked(authModule.refreshToken).mockResolvedValueOnce({
        access_token: "new-access",
        refresh_token: "new-refresh",
        token_type: "bearer",
      });
      vi.mocked(authModule.getAccessToken).mockReturnValue("new-access");

      const make401 = () => ({
        ok: false,
        status: 401,
        statusText: "Unauthorized",
        json: async () => ({ detail: "Token expired" }),
      });

      const makeOk = () => ({
        ok: true,
        status: 200,
        json: async () => ({ data: "ok" }),
      });

      (global.fetch as ReturnType<typeof vi.fn>)
        .mockResolvedValueOnce(make401())
        .mockResolvedValueOnce(make401())
        .mockResolvedValueOnce(makeOk())
        .mockResolvedValueOnce(makeOk());

      const [r1, r2] = await Promise.all([
        apiFetch("/api/v1/endpoint1"),
        apiFetch("/api/v1/endpoint2"),
      ]);

      expect(authModule.refreshToken).toHaveBeenCalledTimes(1);
      expect(r1).toEqual({ data: "ok" });
      expect(r2).toEqual({ data: "ok" });
    });
  });
});

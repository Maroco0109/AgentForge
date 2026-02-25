// REST API fetch wrapper with JWT authentication and auto token refresh

import {
  refreshToken,
  saveTokens,
  getRefreshTokenFromStorage,
  clearTokens,
  getAccessToken,
} from "./auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Mutex to prevent concurrent refresh attempts
let isRefreshing = false;
let refreshPromise: Promise<string | null> | null = null;

// Test-only helper to reset module-level state between tests
export function _resetRefreshState(): void {
  isRefreshing = false;
  refreshPromise = null;
}

async function tryRefresh(): Promise<string | null> {
  const refresh = getRefreshTokenFromStorage();
  if (!refresh) return null;
  try {
    const tokens = await refreshToken(refresh);
    saveTokens(tokens);
    return tokens.access_token;
  } catch (err) {
    console.warn("[apiFetch] Token refresh failed:", err);
    return null;
  }
}

async function refreshOrWait(): Promise<string | null> {
  if (isRefreshing && refreshPromise) return refreshPromise;
  isRefreshing = true;
  refreshPromise = tryRefresh().finally(() => {
    isRefreshing = false;
    refreshPromise = null;
  });
  return refreshPromise;
}

function getAuthHeaders(): Record<string, string> {
  const token = getAccessToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_URL}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      ...getAuthHeaders(),
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    // Handle 401 Unauthorized with token refresh
    if (response.status === 401 && typeof window !== "undefined") {
      // Don't try to refresh if we're already on the refresh endpoint (infinite loop prevention)
      if (path.endsWith("/auth/refresh")) {
        clearTokens();
        window.location.href = "/login";
        return undefined as T;
      }

      // Try to refresh the token
      const newToken = await refreshOrWait();
      if (newToken) {
        // Retry original request with new token
        const retryResponse = await fetch(url, {
          ...options,
          headers: {
            ...getAuthHeaders(),
            ...(options.headers || {}),
          },
        });

        if (retryResponse.ok) {
          if (retryResponse.status === 204) {
            return undefined as T;
          }
          return retryResponse.json();
        }

        // Retry also failed — check if it's another 401
        if (retryResponse.status === 401) {
          clearTokens();
          window.location.href = "/login";
          return undefined as T;
        }

        const retryError = await retryResponse
          .json()
          .catch(() => ({ detail: retryResponse.statusText }));
        const retryDetail = retryError.detail;
        if (Array.isArray(retryDetail)) {
          throw new Error(
            retryDetail
              .map((d: { msg?: string }) => d.msg || "Validation error")
              .join(", ")
          );
        }
        throw new Error(
          typeof retryDetail === "string"
            ? retryDetail
            : `API error: ${retryResponse.status}`
        );
      }

      // Refresh failed — logout
      clearTokens();
      window.location.href = "/login";
      return undefined as T;
    }

    const error = await response
      .json()
      .catch(() => ({ detail: response.statusText }));
    const detail = error.detail;
    if (Array.isArray(detail)) {
      throw new Error(
        detail
          .map((d: { msg?: string }) => d.msg || "Validation error")
          .join(", ")
      );
    }
    throw new Error(
      typeof detail === "string" ? detail : `API error: ${response.status}`
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// LLM Key Management
export interface LLMKeyResponse {
  id: string;
  provider: string;
  key_prefix: string;
  is_active: boolean;
  is_valid: boolean;
  last_used_at: string | null;
  last_validated_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface LLMKeyValidationResponse {
  provider: string;
  is_valid: boolean;
  message: string;
  models_available: string[];
}

export async function listLLMKeys(): Promise<LLMKeyResponse[]> {
  return apiFetch<LLMKeyResponse[]>("/api/v1/llm-keys");
}

export async function registerLLMKey(
  provider: string,
  apiKey: string
): Promise<LLMKeyResponse> {
  return apiFetch<LLMKeyResponse>("/api/v1/llm-keys", {
    method: "POST",
    body: JSON.stringify({ provider, api_key: apiKey }),
  });
}

export async function deleteLLMKey(keyId: string): Promise<void> {
  await apiFetch<void>(`/api/v1/llm-keys/${keyId}`, { method: "DELETE" });
}

export async function validateLLMKey(
  keyId: string
): Promise<LLMKeyValidationResponse> {
  return apiFetch<LLMKeyValidationResponse>(
    `/api/v1/llm-keys/${keyId}/validate`,
    {
      method: "POST",
    }
  );
}

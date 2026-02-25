// REST API fetch wrapper with JWT authentication

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getAuthHeaders(): Record<string, string> {
  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("access_token")
      : null;
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
    // Clear expired/invalid token and redirect to login on 401
    if (response.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      window.location.href = "/login";
      return undefined as T;
    }

    const error = await response.json().catch(() => ({ detail: response.statusText }));
    const detail = error.detail;
    if (Array.isArray(detail)) {
      throw new Error(detail.map((d: { msg?: string }) => d.msg || "Validation error").join(", "));
    }
    throw new Error(typeof detail === "string" ? detail : `API error: ${response.status}`);
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

export async function registerLLMKey(provider: string, apiKey: string): Promise<LLMKeyResponse> {
  return apiFetch<LLMKeyResponse>("/api/v1/llm-keys", {
    method: "POST",
    body: JSON.stringify({ provider, api_key: apiKey }),
  });
}

export async function deleteLLMKey(keyId: string): Promise<void> {
  await apiFetch<void>(`/api/v1/llm-keys/${keyId}`, { method: "DELETE" });
}

export async function validateLLMKey(keyId: string): Promise<LLMKeyValidationResponse> {
  return apiFetch<LLMKeyValidationResponse>(`/api/v1/llm-keys/${keyId}/validate`, {
    method: "POST",
  });
}

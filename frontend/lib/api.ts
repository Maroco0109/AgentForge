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

"use client";

import { useEffect, useState, useCallback } from "react";
import {
  listLLMKeys,
  registerLLMKey,
  LLMKeyResponse,
  LLMKeyValidationResponse,
} from "@/lib/api";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import ProviderCard from "./components/ProviderCard";

const PROVIDERS = ["openai", "anthropic", "google"] as const;
type Provider = (typeof PROVIDERS)[number];

const PROVIDER_LABELS: Record<Provider, string> = {
  openai: "OpenAI",
  anthropic: "Anthropic",
  google: "Google",
};

export default function SettingsPage() {
  const [keys, setKeys] = useState<LLMKeyResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Register dialog state
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogProvider, setDialogProvider] = useState<string>("");
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const fetchKeys = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listLLMKeys();
      setKeys(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load API keys");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchKeys();
  }, [fetchKeys]);

  function openRegisterDialog(provider: string) {
    setDialogProvider(provider);
    setApiKeyInput("");
    setSubmitError(null);
    setDialogOpen(true);
  }

  async function handleRegister() {
    if (!apiKeyInput.trim()) {
      setSubmitError("API key is required");
      return;
    }
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const newKey = await registerLLMKey(dialogProvider, apiKeyInput.trim());
      setKeys((prev) => {
        const filtered = prev.filter((k) => k.provider !== dialogProvider);
        return [...filtered, newKey];
      });
      setDialogOpen(false);
      setApiKeyInput("");
    } catch (err) {
      setSubmitError(
        err instanceof Error ? err.message : "Failed to register key"
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleDeleted(keyId: string) {
    setKeys((prev) => prev.filter((k) => k.id !== keyId));
  }

  function handleValidated(keyId: string, result: LLMKeyValidationResponse) {
    setKeys((prev) =>
      prev.map((k) =>
        k.id === keyId
          ? {
              ...k,
              is_valid: result.is_valid,
              last_validated_at: new Date().toISOString(),
            }
          : k
      )
    );
  }

  function getKeyForProvider(provider: string): LLMKeyResponse | undefined {
    return keys.find((k) => k.provider === provider);
  }

  const registeredCount = PROVIDERS.filter((p) => getKeyForProvider(p)).length;

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-2xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-100">Settings</h1>
          <p className="text-sm text-gray-500 mt-1">
            Manage your LLM provider API keys for BYOK (Bring Your Own Key)
            access.
          </p>
        </div>

        {/* Section heading */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-semibold text-gray-300">
              LLM Provider Keys
            </h2>
            <p className="text-xs text-gray-500 mt-0.5">
              {registeredCount} of {PROVIDERS.length} providers configured
            </p>
          </div>
          {!loading && (
            <button
              onClick={fetchKeys}
              className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
            >
              Refresh
            </button>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="mb-6 text-red-400 text-sm bg-red-900/20 border border-red-800 rounded-md px-4 py-3 flex items-center justify-between">
            <span>{error}</span>
            <button
              onClick={fetchKeys}
              className="text-red-300 hover:text-red-100 text-xs underline ml-4"
            >
              Retry
            </button>
          </div>
        )}

        {/* Provider cards */}
        {loading ? (
          <div className="space-y-3">
            {PROVIDERS.map((p) => (
              <div
                key={p}
                className="bg-gray-900 border border-gray-800 rounded-lg p-5 animate-pulse"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-md bg-gray-800" />
                  <div className="space-y-1.5">
                    <div className="h-3 w-20 bg-gray-800 rounded" />
                    <div className="h-2.5 w-40 bg-gray-800 rounded" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-3">
            {PROVIDERS.map((provider) => (
              <ProviderCard
                key={provider}
                provider={provider}
                keyData={getKeyForProvider(provider)}
                onRegister={openRegisterDialog}
                onDeleted={handleDeleted}
                onValidated={handleValidated}
              />
            ))}
          </div>
        )}

        {/* Info note */}
        <div className="mt-6 text-xs text-gray-600 bg-gray-900/50 border border-gray-800 rounded-md px-4 py-3">
          Keys are stored encrypted and never exposed in full. Only the key
          prefix is displayed for identification.
        </div>
      </div>

      {/* Register / Update Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="bg-gray-900 border-gray-800 text-gray-100 sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-gray-100">
              {getKeyForProvider(dialogProvider) ? "Update" : "Add"}{" "}
              {PROVIDER_LABELS[dialogProvider as Provider] ?? dialogProvider} Key
            </DialogTitle>
            <DialogDescription className="text-gray-500">
              Enter your API key. It will be stored encrypted and never shown in
              full again.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label htmlFor="api-key-input" className="text-xs text-gray-400">
                API Key
              </Label>
              <input
                id="api-key-input"
                type="password"
                value={apiKeyInput}
                onChange={(e) => setApiKeyInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !isSubmitting) handleRegister();
                }}
                placeholder={
                  dialogProvider === "openai"
                    ? "sk-..."
                    : dialogProvider === "anthropic"
                    ? "sk-ant-..."
                    : "AIza..."
                }
                autoComplete="off"
                className="w-full bg-gray-800 text-gray-100 border border-gray-700 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent placeholder:text-gray-600 font-mono"
              />
            </div>

            {submitError && (
              <p className="text-xs text-red-400 bg-red-900/20 border border-red-800/50 rounded-md px-3 py-2">
                {submitError}
              </p>
            )}
          </div>

          <DialogFooter>
            <button
              onClick={() => setDialogOpen(false)}
              disabled={isSubmitting}
              className="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 hover:bg-gray-800 rounded-md transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={handleRegister}
              disabled={isSubmitting || !apiKeyInput.trim()}
              className="px-4 py-2 text-sm bg-primary-600 hover:bg-primary-700 text-white rounded-md font-medium transition-colors disabled:opacity-50"
            >
              {isSubmitting ? "Saving..." : "Save Key"}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

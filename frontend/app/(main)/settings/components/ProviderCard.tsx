"use client";

import { useState } from "react";
import {
  LLMKeyResponse,
  LLMKeyValidationResponse,
  deleteLLMKey,
  validateLLMKey,
} from "@/lib/api";

interface ProviderMeta {
  name: string;
  description: string;
  color: string;
  bgColor: string;
  borderColor: string;
  docsUrl: string;
}

const PROVIDER_META: Record<string, ProviderMeta> = {
  openai: {
    name: "OpenAI",
    description: "GPT-4o, GPT-4 Turbo, GPT-3.5 Turbo",
    color: "#10a37f",
    bgColor: "bg-emerald-900/20",
    borderColor: "border-emerald-800/50",
    docsUrl: "https://platform.openai.com/api-keys",
  },
  anthropic: {
    name: "Anthropic",
    description: "Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku",
    color: "#d97706",
    bgColor: "bg-amber-900/20",
    borderColor: "border-amber-800/50",
    docsUrl: "https://console.anthropic.com/settings/keys",
  },
  google: {
    name: "Google",
    description: "Gemini 1.5 Pro, Gemini 1.5 Flash, Gemini Pro",
    color: "#4285f4",
    bgColor: "bg-blue-900/20",
    borderColor: "border-blue-800/50",
    docsUrl: "https://aistudio.google.com/app/apikey",
  },
};

interface ProviderCardProps {
  provider: string;
  keyData: LLMKeyResponse | undefined;
  onRegister: (provider: string) => void;
  onDeleted: (keyId: string) => void;
  onValidated: (keyId: string, result: LLMKeyValidationResponse) => void;
}

export default function ProviderCard({
  provider,
  keyData,
  onRegister,
  onDeleted,
  onValidated,
}: ProviderCardProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [validationResult, setValidationResult] =
    useState<LLMKeyValidationResponse | null>(null);

  const meta = PROVIDER_META[provider] ?? {
    name: provider,
    description: "LLM Provider",
    color: "#6b7280",
    bgColor: "bg-gray-900/20",
    borderColor: "border-gray-800/50",
    docsUrl: "#",
  };

  const isRegistered = !!keyData;

  async function handleDelete() {
    if (!keyData) return;
    setIsDeleting(true);
    setActionError(null);
    try {
      await deleteLLMKey(keyData.id);
      setShowDeleteConfirm(false);
      setValidationResult(null);
      onDeleted(keyData.id);
    } catch (err) {
      setActionError(
        err instanceof Error ? err.message : "Failed to delete key"
      );
    } finally {
      setIsDeleting(false);
    }
  }

  async function handleValidate() {
    if (!keyData) return;
    setIsValidating(true);
    setActionError(null);
    setValidationResult(null);
    try {
      const result = await validateLLMKey(keyData.id);
      setValidationResult(result);
      onValidated(keyData.id, result);
    } catch (err) {
      setActionError(
        err instanceof Error ? err.message : "Failed to validate key"
      );
    } finally {
      setIsValidating(false);
    }
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div
            className="w-8 h-8 rounded-md flex items-center justify-center text-xs font-bold flex-shrink-0"
            style={{ backgroundColor: `${meta.color}22`, color: meta.color }}
          >
            {meta.name.slice(0, 2).toUpperCase()}
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-100">{meta.name}</h3>
            <p className="text-xs text-gray-500 mt-0.5">{meta.description}</p>
          </div>
        </div>

        {/* Status badge */}
        {isRegistered ? (
          <span
            className={`text-[10px] font-medium px-2 py-1 rounded-full flex-shrink-0 ${
              keyData.is_valid
                ? "bg-emerald-900/40 text-emerald-400 border border-emerald-800/50"
                : "bg-red-900/40 text-red-400 border border-red-800/50"
            }`}
          >
            {keyData.is_valid ? "Valid" : "Invalid"}
          </span>
        ) : (
          <span className="text-[10px] font-medium px-2 py-1 rounded-full bg-gray-800 text-gray-500 border border-gray-700 flex-shrink-0">
            Not configured
          </span>
        )}
      </div>

      {/* Key info */}
      {isRegistered && (
        <div className="mb-4 space-y-1.5">
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500 w-24 flex-shrink-0">Key prefix</span>
            <code className="text-xs text-gray-300 font-mono bg-gray-800 px-2 py-0.5 rounded">
              {keyData.key_prefix}...
            </code>
          </div>
          {keyData.last_validated_at && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 w-24 flex-shrink-0">Last validated</span>
              <span className="text-xs text-gray-400">
                {new Date(keyData.last_validated_at).toLocaleString()}
              </span>
            </div>
          )}
          {keyData.last_used_at && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 w-24 flex-shrink-0">Last used</span>
              <span className="text-xs text-gray-400">
                {new Date(keyData.last_used_at).toLocaleString()}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Validation result */}
      {validationResult && (
        <div
          className={`mb-4 rounded-md px-3 py-2 text-xs border ${
            validationResult.is_valid
              ? "bg-emerald-900/20 border-emerald-800/50 text-emerald-400"
              : "bg-red-900/20 border-red-800/50 text-red-400"
          }`}
        >
          <p className="font-medium">{validationResult.message}</p>
          {validationResult.models_available.length > 0 && (
            <p className="mt-1 text-gray-400">
              Models: {validationResult.models_available.slice(0, 3).join(", ")}
              {validationResult.models_available.length > 3 &&
                ` +${validationResult.models_available.length - 3} more`}
            </p>
          )}
        </div>
      )}

      {/* Action error */}
      {actionError && (
        <div className="mb-4 text-xs text-red-400 bg-red-900/20 border border-red-800/50 rounded-md px-3 py-2">
          {actionError}
        </div>
      )}

      {/* Delete confirmation */}
      {showDeleteConfirm && (
        <div className="mb-4 bg-red-900/10 border border-red-800/50 rounded-md px-3 py-3">
          <p className="text-xs text-red-300 mb-3">
            Remove this API key? This cannot be undone.
          </p>
          <div className="flex gap-2">
            <button
              onClick={handleDelete}
              disabled={isDeleting}
              className="px-3 py-1.5 text-xs bg-red-700 hover:bg-red-600 text-white rounded-md transition-colors disabled:opacity-50"
            >
              {isDeleting ? "Removing..." : "Remove"}
            </button>
            <button
              onClick={() => setShowDeleteConfirm(false)}
              disabled={isDeleting}
              className="px-3 py-1.5 text-xs text-gray-400 hover:text-gray-200 hover:bg-gray-800 rounded-md transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={() => onRegister(provider)}
          className="px-3 py-1.5 text-xs font-medium rounded-md transition-colors"
          style={{
            backgroundColor: `${meta.color}22`,
            color: meta.color,
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLButtonElement).style.backgroundColor = `${meta.color}33`;
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLButtonElement).style.backgroundColor = `${meta.color}22`;
          }}
        >
          {isRegistered ? "Update Key" : "Add Key"}
        </button>

        {isRegistered && (
          <>
            <button
              onClick={handleValidate}
              disabled={isValidating || isDeleting}
              className="px-3 py-1.5 text-xs text-gray-400 hover:text-gray-200 hover:bg-gray-800 border border-gray-700 hover:border-gray-600 rounded-md transition-colors disabled:opacity-50"
            >
              {isValidating ? "Validating..." : "Re-validate"}
            </button>
            {!showDeleteConfirm && (
              <button
                onClick={() => {
                  setShowDeleteConfirm(true);
                  setActionError(null);
                }}
                className="px-3 py-1.5 text-xs text-red-500 hover:text-red-400 hover:bg-red-900/20 border border-red-900/50 hover:border-red-800 rounded-md transition-colors"
              >
                Remove
              </button>
            )}
          </>
        )}

        <a
          href={meta.docsUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="ml-auto text-xs text-gray-600 hover:text-gray-400 transition-colors"
        >
          Get key
        </a>
      </div>
    </div>
  );
}

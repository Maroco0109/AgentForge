// Default settings for each agent role

export interface RoleConfig {
  label: string;
  color: string;
  defaultModel: string;
  icon: string;
  defaultTemperature: number;
  defaultMaxTokens: number;
  defaultRetryCount: number;
}

export const ROLE_CONFIGS: Record<string, RoleConfig> = {
  collector: {
    label: "Collector",
    color: "#3b82f6", // blue
    defaultModel: "gpt-4o-mini",
    icon: "📥",
    defaultTemperature: 0.3,
    defaultMaxTokens: 4096,
    defaultRetryCount: 3,
  },
  analyzer: {
    label: "Analyzer",
    color: "#8b5cf6", // violet
    defaultModel: "gpt-4o",
    icon: "🔍",
    defaultTemperature: 0.7,
    defaultMaxTokens: 4096,
    defaultRetryCount: 3,
  },
  validator: {
    label: "Validator",
    color: "#f59e0b", // amber
    defaultModel: "gpt-4o-mini",
    icon: "✅",
    defaultTemperature: 0.2,
    defaultMaxTokens: 2048,
    defaultRetryCount: 3,
  },
  reporter: {
    label: "Reporter",
    color: "#10b981", // emerald
    defaultModel: "gpt-4o-mini",
    icon: "📊",
    defaultTemperature: 0.5,
    defaultMaxTokens: 4096,
    defaultRetryCount: 3,
  },
  synthesizer: {
    label: "Synthesizer",
    color: "#ec4899", // pink
    defaultModel: "gpt-4o",
    icon: "🧬",
    defaultTemperature: 0.7,
    defaultMaxTokens: 4096,
    defaultRetryCount: 3,
  },
  critic: {
    label: "Critic",
    color: "#ef4444", // red
    defaultModel: "gpt-4o",
    icon: "🎯",
    defaultTemperature: 0.5,
    defaultMaxTokens: 4096,
    defaultRetryCount: 3,
  },
  cross_checker: {
    label: "Cross Checker",
    color: "#f97316", // orange
    defaultModel: "gpt-4o",
    icon: "🔄",
    defaultTemperature: 0.5,
    defaultMaxTokens: 4096,
    defaultRetryCount: 3,
  },
};

export const AVAILABLE_ROLES = Object.keys(ROLE_CONFIGS);

export const AVAILABLE_MODELS = [
  "gpt-4o",
  "gpt-4o-mini",
  "claude-sonnet-4-5",
  "claude-haiku-4-5",
];

const DEFAULT_ROLE_CONFIG: RoleConfig = {
  label: "Custom",
  color: "#6b7280",
  defaultModel: "gpt-4o-mini",
  icon: "⚙️",
  defaultTemperature: 0.7,
  defaultMaxTokens: 4096,
  defaultRetryCount: 3,
};

export function getRoleConfig(role: string): RoleConfig {
  return ROLE_CONFIGS[role] || { ...DEFAULT_ROLE_CONFIG, label: role };
}

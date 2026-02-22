// Default settings for each agent role

export interface RoleConfig {
  label: string;
  color: string;
  defaultModel: string;
  icon: string;
}

export const ROLE_CONFIGS: Record<string, RoleConfig> = {
  collector: {
    label: "Collector",
    color: "#3b82f6", // blue
    defaultModel: "gpt-4o-mini",
    icon: "📥",
  },
  analyzer: {
    label: "Analyzer",
    color: "#8b5cf6", // violet
    defaultModel: "gpt-4o",
    icon: "🔍",
  },
  validator: {
    label: "Validator",
    color: "#f59e0b", // amber
    defaultModel: "gpt-4o-mini",
    icon: "✅",
  },
  reporter: {
    label: "Reporter",
    color: "#10b981", // emerald
    defaultModel: "gpt-4o-mini",
    icon: "📊",
  },
  synthesizer: {
    label: "Synthesizer",
    color: "#ec4899", // pink
    defaultModel: "gpt-4o",
    icon: "🧬",
  },
  critic: {
    label: "Critic",
    color: "#ef4444", // red
    defaultModel: "gpt-4o",
    icon: "🎯",
  },
  cross_checker: {
    label: "Cross Checker",
    color: "#f97316", // orange
    defaultModel: "gpt-4o",
    icon: "🔄",
  },
};

export const AVAILABLE_ROLES = Object.keys(ROLE_CONFIGS);

export const AVAILABLE_MODELS = [
  "gpt-4o",
  "gpt-4o-mini",
  "claude-sonnet-4-5",
  "claude-haiku-4-5",
];

export function getRoleConfig(role: string): RoleConfig {
  return (
    ROLE_CONFIGS[role] || {
      label: role,
      color: "#6b7280",
      defaultModel: "gpt-4o-mini",
      icon: "⚙️",
    }
  );
}

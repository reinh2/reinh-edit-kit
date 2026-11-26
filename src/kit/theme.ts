// Your look in one place: colours, font and texts come from kit.config.json (repository root).
import config from "../../kit.config.json";

export const KIT = config;
export const C = {
  accent: config.brand.accent,
  ink: config.brand.ink,
  muted: config.brand.muted,
  page: config.brand.page,
  white: "#FFFFFF",
  track: "#EEF1F6",
  red: "#E5484D",
  green: "#2FB36B",
};
export const FONT = `${config.brand.font}, Inter, Arial, sans-serif`;
export const MONO = "'JetBrains Mono', Menlo, monospace";
export const shadow = "0 18px 50px rgba(0,0,0,0.16), 0 3px 10px rgba(0,0,0,0.08)";
export const PAGE_BG = `radial-gradient(90% 60% at 30% 20%, #FFFFFF 0%, ${config.brand.page} 55%, #E9EDF4 100%)`;
export const abs = (s: React.CSSProperties): React.CSSProperties => ({ position: "absolute", boxSizing: "border-box", ...s });

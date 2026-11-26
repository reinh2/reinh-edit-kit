// Animation themes: the same insert can be drawn light (white cards on a light page, Inter, one accent) or «cine»
// (dark navy depth, glass panels, huge condensed chrome words in the back layer, grain). Pick per video or per scene:
//   <KitTheme name="cine"> …scenes… </KitTheme>   and inside a component:   const th = useTheme();
// Rule of thumb from a real long video: big moments (hook, chapter, result, ending) in cine, explanations in light,
// a light leak (chapter.tsx) on every switch between them. Default comes from kit.config.json «style».
import React, { createContext, useContext } from "react";
import { AbsoluteFill } from "remotion";
import { CineBg, Chrome, loadCineFonts } from "./cine";
import { C, KIT, PAGE_BG } from "./theme";

export type ThemeName = "light" | "cine";
export type Theme = {
  name: ThemeName;
  ink: string; muted: string; accent: string; track: string;
  /** filled element (selected item, CTA pill) and the text on it */ solid: string; onSolid: string;
  /** neutral chip: background and border */ chip: string; chipBorder: string;
  card: React.CSSProperties;
  Bg: React.FC<{ t: number }>;
  /** the big back-layer word of a scene (cine only; light draws nothing) */ BackWord: React.FC<{ text: string; t: number; at?: number; top?: number }>;
};

const SHADOW = "0 24px 70px rgba(17,19,24,0.14), 0 3px 10px rgba(17,19,24,0.06)";

export const THEMES: Record<ThemeName, Theme> = {
  light: {
    name: "light", ink: C.ink, muted: C.muted, accent: C.accent, track: C.track, solid: C.ink, onSolid: "#FFFFFF",
    chip: "#FFFFFF", chipBorder: "#E3E7EF",
    card: { background: "rgba(255,255,255,0.97)", boxShadow: SHADOW },
    Bg: () => <AbsoluteFill style={{ background: PAGE_BG }} />,
    BackWord: () => null,
  },
  cine: {
    name: "cine", ink: "#FFFFFF", muted: "#8E9BB6", accent: C.accent, track: "rgba(160,190,255,0.16)", solid: C.accent, onSolid: "#FFFFFF",
    chip: "rgba(20,30,52,0.72)", chipBorder: "rgba(170,200,255,0.28)",
    card: { background: "rgba(20,30,52,0.72)", border: "1px solid rgba(170,200,255,0.28)", backdropFilter: "blur(10px)",
      boxShadow: `0 40px 120px rgba(0,0,0,0.55), 0 0 80px ${C.accent}47, inset 0 1px 0 rgba(255,255,255,0.18)` },
    Bg: ({ t }) => { loadCineFonts(); return <CineBg t={t} />; },
    BackWord: ({ text, t, at = 0.05, top = 300 }) => <Chrome text={text} size={300} t={t} at={at} dim={0.16} style={{ left: 0, right: 0, top, textAlign: "center" }} />,
  },
};

const Ctx = createContext<Theme>(THEMES[((KIT as { style?: ThemeName }).style ?? "light") as ThemeName] ?? THEMES.light);
export const KitTheme: React.FC<{ name: ThemeName; children: React.ReactNode }> = ({ name, children }) => <Ctx.Provider value={THEMES[name]}>{children}</Ctx.Provider>;
export const useTheme = () => useContext(Ctx);

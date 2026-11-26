// Promo + guide for Reinh Edit Kit (16:9, 2560×1440, 60 fps): what the kit is, four steps to start, the two animation
// styles (changed through the agent in plain words), honest limits, where to get it. Built with the kit's own pieces.
// Three variants of the same film (prop `variant`):
//   light — every scene light (white cards, Inter, one accent);
//   cine  — every scene cine (dark navy, glass, chrome back words, grain);
//   mix   — big moments cine (hook, inside, styles, limits, ending), the four guide steps light — like a real long video;
// a light leak covers every scene change. 3D heroes (Blender, `npm run promo:3d`): a film slate snaps on the cut in the hook,
// five real microphones take turns in step 2, the kit's equipment case opens at the end; without renders the scenes keep their flat layout. Authored on a 1920×1080 grid and scaled (Fit).
// Voice-over text: src/promo/script.json; scratch synthetic voice for pacing: `npm run promo:vo` (the final voice-over
// is recorded by a person). Scene lengths = max(min, voice + 0.6 s). No music here: add the bed with mix_bed.py.
import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { LightLeak } from "../kit/chapter";
import { Hero3D, type HeroMeta } from "../kit/Hero3D";
import { loadCineFonts } from "../kit/cine";
import { loadBaseFonts } from "../kit/fonts";
import { clamp01, ease, impulse, lerp, prog, typed } from "../kit/motion";
import { KitTheme, THEMES, useTheme, type ThemeName } from "../kit/themes";
import script from "./script.json";

export const PROMO_FPS = 60;
const W = 1920, H = 1080;
const ACCENT = "#5B8CFF", GREEN = "#2FB36B", RED = "#E5484D";
const FONT = "Inter, Arial, sans-serif", MONO = "'JetBrains Mono', Menlo, monospace";
const abs = (s: React.CSSProperties): React.CSSProperties => ({ position: "absolute", boxSizing: "border-box", ...s });
const rise = (p: number, dy = 24): React.CSSProperties => ({ opacity: clamp01(p), filter: `blur(${(1 - clamp01(p)) * 10}px)`, transform: `translateY(${(1 - p) * dy}px)` });

export type PromoVariant = "light" | "cine" | "mix";
// real popular microphones as procedural 3D models (scripts/blender/mics.py → public/mics3d/<id>/, `npm run mics:3d`)
export const MIC_MODELS = [["yeti", "Blue Yeti"], ["solocast", "HyperX SoloCast"], ["sm7b", "Shure SM7B"], ["podmic", "Rode PodMic"], ["dji", "DJI Mic Mini 2"]] as const;
export type MicId = (typeof MIC_MODELS)[number][0];
export type PromoHeroes = Partial<Record<"clapper" | "case", HeroMeta | null>> & { mics?: Partial<Record<MicId, HeroMeta | null>> };
export type PromoProps = { vo: Record<string, number> | null; variant: PromoVariant; heroes?: PromoHeroes };
export const HERO_NAMES = ["clapper", "case"] as const;
const HeroCtx = React.createContext<PromoHeroes>({});
const useHero = (n: "clapper" | "case") => React.useContext(HeroCtx)[n] ?? null;
const useMics = () => React.useContext(HeroCtx).mics ?? {};
type SceneId = (typeof script.scenes)[number]["id"];
export const sceneDurations = (vo: PromoProps["vo"]) => script.scenes.map((s) => Math.max(s.min, vo?.[s.id] ? vo[s.id] + 0.6 : 0));
export const promoFrames = (vo: PromoProps["vo"]) => Math.round(sceneDurations(vo).reduce((a, b) => a + b, 0) * PROMO_FPS);
const MIX: Record<string, ThemeName> = { hook: "cine", pipeline: "cine", install: "light", mic: "light", agent: "light", qc: "light", styles: "cine", limits: "cine", cta: "cine" };
const themeOf = (variant: PromoVariant, id: string): ThemeName => (variant === "mix" ? MIX[id] ?? "light" : variant);

const useT = () => useCurrentFrame() / useVideoConfig().fps;

// sounds of the quiet v3 pack (npm run sfx)
const S: React.FC<{ at: number; f: string; db?: number }> = ({ at, f, db = -14 }) => (
  <Sequence from={Math.max(0, Math.round(at * PROMO_FPS) - 2)} layout="none">
    <Audio src={staticFile(`sfx/v3/${f}.wav`)} volume={Math.pow(10, db / 20)} />
  </Sequence>
);

const Fit: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { width } = useVideoConfig();
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <div style={abs({ left: 0, top: 0, width: W, height: H, transformOrigin: "0 0", transform: `scale(${width / W})`, overflow: "hidden" })}>{children}</div>
    </AbsoluteFill>
  );
};

// drawn line icons (24 × 24)
const IC: Record<string, string> = {
  film: "M4 4h16v16H4z M8 4v16 M16 4v16 M4 8h4 M4 12h4 M4 16h4 M16 8h4 M16 12h4 M16 16h4",
  scissors: "M6 6.5a2.5 2.5 0 1 0 0 .01 M6 17.5a2.5 2.5 0 1 0 0 .01 M8 8l12 9 M8 16l12-9",
  wave: "M3 12h2 M7 8v8 M11 5v14 M15 9v6 M19 11v2",
  shapes: "M4 14h7v7H4z M17.5 3.5l4 7h-8z M17.5 14.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7z",
  check: "M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z M8.5 12l2.5 2.5 4.5-5",
  play: "M4 5h16v14H4z M10 9l5 3-5 3z",
  mic: "M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3z M5.5 11a6.5 6.5 0 0 0 13 0 M12 17.5V21",
  lav: "M12 4a2 2 0 0 0-2 2v4a2 2 0 0 0 4 0V6a2 2 0 0 0-2-2z M12 12v9 M9 14h6",
  headset: "M4 14v-2a8 8 0 0 1 16 0v2 M4 14h3v5H4z M17 14h3v5h-3z M20 19c0 1.5-2 2.5-5 2.5h-2",
  phone: "M8 2.5h8a1.5 1.5 0 0 1 1.5 1.5v16a1.5 1.5 0 0 1-1.5 1.5H8A1.5 1.5 0 0 1 6.5 20V4A1.5 1.5 0 0 1 8 2.5z M11 18.5h2",
  dynamic: "M9 3h6v8a3 3 0 0 1-6 0z M9 6h6 M9 8.5h6 M12 14v7 M8.5 21h7",
  user: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M4.5 20a7.5 7.5 0 0 1 15 0",
  send: "M14.5 21.7a.5.5 0 0 0 .9 0l6.5-19a.5.5 0 0 0-.6-.6l-19 6.5a.5.5 0 0 0 0 .9l7.9 3.2a2 2 0 0 1 1.1 1.1z M21.9 2.1 10.9 13.1",
  tick: "M5 12.5l4.5 4.5L19 7.5",
};
const Icon: React.FC<{ d: string; size: number; color?: string; sw?: number }> = ({ d, size, color, sw = 1.9 }) => {
  const th = useTheme();
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" style={{ display: "block", flex: "none" }}>
      <path d={d} fill="none" stroke={color ?? th.ink} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
};
const Tick: React.FC<{ size?: number }> = ({ size = 46 }) => (
  <div style={{ width: size, height: size, borderRadius: 99, background: GREEN, display: "flex", alignItems: "center", justifyContent: "center", flex: "none" }}><Icon d={IC.tick} size={size * 0.65} color="#fff" sw={3} /></div>
);

// scene frame: themed background, the big back word (cine), the step label
const Scene: React.FC<{ t: number; back?: string; n?: number; label?: string; children: React.ReactNode }> = ({ t, back, n, label, children }) => {
  const th = useTheme();
  if (th.name === "cine") loadCineFonts();
  const p = prog(t, 0.05, 0.45, ease.outBack);
  return (
    <AbsoluteFill>
      <th.Bg t={t} />
      {back && <th.BackWord text={back} t={t} top={th.name === "cine" ? 330 : 300} />}
      {label && (
        <div style={abs({ left: 110, top: 90, display: "flex", alignItems: "center", gap: 18, opacity: clamp01(p * 2), transform: `translateX(${(1 - p) * -30}px)` })}>
          {n && <div style={{ width: 64, height: 64, borderRadius: 20, background: th.accent, color: "#fff", fontFamily: FONT, fontWeight: 800, fontSize: 36, display: "flex", alignItems: "center", justifyContent: "center" }}>{n}</div>}
          <div style={{ fontFamily: FONT, fontWeight: 750, fontSize: 40, color: th.ink, letterSpacing: "-0.02em" }}>{label}</div>
        </div>
      )}
      {children}
    </AbsoluteFill>
  );
};

const Card: React.FC<{ style: React.CSSProperties; p?: number; children: React.ReactNode; dark?: boolean }> = ({ style, p = 1, children, dark }) => {
  const th = useTheme();
  return <div style={abs({ borderRadius: 34, ...(dark ? { background: "#0F1218", boxShadow: th.card.boxShadow, border: th.name === "cine" ? "1px solid rgba(170,200,255,0.2)" : undefined } : th.card), ...rise(p), ...style })}>{children}</div>;
};

const Chip: React.FC<{ text: string; p: number; solid?: boolean; size?: number }> = ({ text, p, solid, size = 44 }) => {
  const th = useTheme();
  return (
    <div style={{ padding: `${size * 0.4}px ${size * 0.86}px`, borderRadius: 999, background: solid ? th.solid : th.chip, color: solid ? th.onSolid : th.ink, border: solid ? "none" : `2px solid ${th.chipBorder}`,
      fontFamily: FONT, fontWeight: 750, fontSize: size, whiteSpace: "nowrap", opacity: clamp01(p * 2), transform: `scale(${lerp(0.85, 1, p)})` }}>{text}</div>
  );
};

// ---------------------------------------------------------------- 1. hook: a strip of takes, a cut closes the gap
const Hook: React.FC = () => {
  const t = useT();
  const th = useTheme();
  const CUT = 1.5;
  const close = prog(t, CUT, 0.55, ease.inOutCubic);
  const words = ["Монтаж", "с ИИ"];
  const pill = prog(t, 2.2, 0.5, ease.outBack);
  const cine = th.name === "cine";
  const hero = useHero("clapper");
  const top = hero ? 110 : 250;
  return (
    <Scene t={t}>
      {hero && <Hero3D dir="promo3d/clapper" meta={hero} style={{ left: 496, top: 250, width: 912, height: 760 }} fadeIn={0.05} />}
      {!hero && <div style={abs({ left: 0, top: 690, width: W, height: 170, overflow: "hidden" })}>
        <div style={{ display: "flex", gap: 14, transform: `translateX(${-60 - t * 40}px)` }}>
          {Array.from({ length: 16 }, (_, i) => {
            const pause = i >= 6 && i <= 8;
            return (
              <div key={i} style={{ width: pause ? lerp(150, 0, close) : 150, marginRight: pause ? lerp(0, -14, close) : 0, height: 150, flex: "none", borderRadius: 18,
                background: pause ? `repeating-linear-gradient(135deg, ${cine ? "rgba(255,90,95,0.35)" : "#DCE1EA"} 0 12px, ${cine ? "rgba(255,90,95,0.12)" : "#E9EDF4"} 12px 24px)`
                  : cine ? ["#1B2A48", "#26385E", "#33497A"][i % 3] : ["#2A3140", "#39445A", "#4A5A7A"][i % 3],
                border: cine && !pause ? "1px solid rgba(170,200,255,0.25)" : "none", opacity: pause ? 1 - close * 0.6 : 1, boxShadow: "0 10px 30px rgba(0,0,0,0.18)" }} />
            );
          })}
        </div>
      </div>}
      {!hero && t > CUT - 0.3 && t < CUT + 0.6 && <div style={abs({ left: 0, top: 670, width: W, height: 210, background: `linear-gradient(90deg, transparent, rgba(91,140,255,${0.25 * (1 - prog(t, CUT, 0.6))}), transparent)` })} />}
      <div style={abs({ left: 0, width: W, top, textAlign: "center" })}>
        {words.map((w, i) => {
          const p = prog(t, 0.15 + i * 0.22, 0.6, ease.outExpo);
          return <span key={w} style={{ display: "inline-block", margin: "0 22px", fontFamily: FONT, fontWeight: 850, fontSize: 190, letterSpacing: "-0.045em", color: i ? th.accent : th.ink, textShadow: cine ? "0 20px 60px rgba(0,0,0,0.5)" : "none", ...rise(p, 40) }}>{w}</span>;
        })}
      </div>
      <div style={abs({ left: 0, width: W, top: hero ? 968 : top + 250, display: "flex", justifyContent: "center", gap: 18 })}>
        <Chip text="вся система" p={pill} /><Chip text="бесплатно" p={pill} solid />
      </div>
      <S at={0.15} f="in" /><S at={CUT} f={hero ? "stamp" : "whoosh"} db={hero ? -10 : -16} /><S at={2.2} f="land" />
    </Scene>
  );
};

// ---------------------------------------------------------------- 2. pipeline: six stations light up along a line
const STATIONS: [string, string][] = [["film", "Дубли"], ["scissors", "Паузы"], ["wave", "Звук"], ["shapes", "Графика"], ["check", "Проверка"], ["play", "Ролик"]];
const Pipeline: React.FC = () => {
  const t = useT();
  const th = useTheme();
  const x0 = 210, step = 300, y = 470;
  const line = prog(t, 0.3, 3.2, ease.inOutCubic);
  const bottom = prog(t, 3.9, 0.5, ease.outCubic);
  const off = th.name === "cine" ? "rgba(160,190,255,0.35)" : "#B9BFCA";
  return (
    <Scene t={t} label="Что внутри">
      <svg width={W} height={H} style={abs({ left: 0, top: 0 })}>
        <line x1={x0} y1={y} x2={x0 + step * 5} y2={y} stroke={th.track} strokeWidth={10} strokeLinecap="round" />
        <line x1={x0} y1={y} x2={x0 + step * 5 * line} y2={y} stroke={th.accent} strokeWidth={10} strokeLinecap="round" />
        <circle cx={x0 + step * 5 * line} cy={y} r={line > 0 && line < 1 ? 16 : 0} fill={th.accent} />
      </svg>
      {STATIONS.map(([ic, label], i) => {
        const at = 0.3 + (3.2 * i) / 5 - 0.15;
        const p = prog(t, at, 0.45, ease.outBack);
        const on = t >= at + 0.15;
        return (
          <div key={label} style={abs({ left: x0 + step * i - 95, top: y - 95, width: 190, display: "flex", flexDirection: "column", alignItems: "center", gap: 26 })}>
            <div style={{ width: 190, height: 190, borderRadius: 52, ...(on ? th.card : { background: th.chip, border: `2px solid ${th.chipBorder}` }), outline: on && i === 5 ? `3px solid ${th.accent}` : "none",
              display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${lerp(0.82, 1, p) + impulse(t, at + 0.15, 14, 9) * 0.04})` }}>
              <Icon d={IC[ic]} size={92} color={on ? (i === 5 ? th.accent : th.ink) : off} />
            </div>
            <div style={{ fontFamily: FONT, fontWeight: 750, fontSize: 38, color: on ? th.ink : off }}>{label}</div>
          </div>
        );
      })}
      <div style={abs({ left: 0, width: W, top: 800, display: "flex", justifyContent: "center", gap: 22, ...rise(bottom) })}>
        {[["6", "скиллов для агента"], ["17", "скриптов"], ["2", "стиля анимации"]].map(([n, s]) => (
          <div key={s} style={{ display: "flex", alignItems: "baseline", gap: 14, padding: "20px 34px", borderRadius: 26, ...th.card, fontFamily: FONT }}>
            <span style={{ fontWeight: 850, fontSize: 56, color: th.accent }}>{n}</span><span style={{ fontWeight: 650, fontSize: 34, color: th.ink }}>{s}</span>
          </div>
        ))}
      </div>
      {STATIONS.map((_, i) => <S key={i} at={0.3 + (3.2 * i) / 5} f="tick" db={-20} />)}
      <S at={3.9} f="tap" />
    </Scene>
  );
};

// ---------------------------------------------------------------- 3. install: clone + one command, then everything it sets up
const CMDS = ["git clone …/reinh-edit-kit", "cd reinh-edit-kit && bash install.sh"];
const CHECKS = ["ffmpeg", "whisper.cpp", "Node.js", "модель Whisper", "Remotion", "звуки", "скиллы", "тесты"];
const Install: React.FC = () => {
  const t = useT();
  const card = prog(t, 0.2, 0.5, ease.outCubic);
  let at = 0.6;
  const starts = CMDS.map((c) => { const s = at; at += c.length / 40 + 0.35; return s; });
  const doc = at;
  return (
    <Scene t={t} n={1} label="Установка одной командой" back="установка">
      <Card dark p={card} style={{ left: 260, top: 220, width: 1400, height: 700, padding: "34px 50px" }}>
        <div style={{ display: "flex", gap: 12, marginBottom: 36 }}>{["#FF5F57", "#FEBC2E", "#28C840"].map((c) => <div key={c} style={{ width: 16, height: 16, borderRadius: 99, background: c }} />)}</div>
        {CMDS.map((c, i) => {
          const n = typed(t, starts[i], c, 40, i + 3);
          return <div key={c} style={{ fontFamily: MONO, fontSize: 34, lineHeight: 1.75, color: "#E6E9EF", whiteSpace: "pre" }}><span style={{ color: ACCENT }}>{n > 0 ? "$ " : ""}</span>{c.slice(0, n)}{n > 0 && n < c.length ? "▍" : ""}</div>;
        })}
        <div style={{ display: "flex", flexWrap: "wrap", gap: "10px 0", marginTop: 30 }}>
          {CHECKS.map((c, i) => <div key={c} style={{ fontFamily: MONO, fontSize: 34, color: GREEN, opacity: prog(t, doc + 0.2 + i * 0.28, 0.3), width: 600 }}>✓ {c}</div>)}
        </div>
      </Card>
      {CMDS.map((_, i) => <S key={i} at={starts[i]} f="tap" db={-22} />)}
      {CHECKS.map((_, i) => <S key={`c${i}`} at={doc + 0.2 + i * 0.28} f="tick" db={-24} />)}
      <S at={doc + 0.2 + CHECKS.length * 0.28} f="success" />
    </Scene>
  );
};

// ---------------------------------------------------------------- 4. mic: any mic → analyze → bands → preset
const MICS: [string, string][] = [["mic", "USB"], ["dynamic", "динамический"], ["lav", "петличка"], ["headset", "гарнитура"], ["phone", "телефон"]];
const BANDS = [125, 250, 500, "1k", "2k", "4k", "8k"];
const DEV = [-1.5, 2.6, -0.4, 1.8, -3.2, -4.1, 1.2]; // an illustrative «before» against the average voice
const SLOT = 0.62, SLOT0 = 0.25; // the 3D mics take turns: one per slot, the last one stays
const Mic: React.FC = () => {
  const t = useT();
  const th = useTheme();
  const mics = useMics();
  const real = MIC_MODELS.some(([id]) => mics[id]);
  const n = real ? MIC_MODELS.length : MICS.length;
  const sel = real ? Math.max(0, Math.min(n - 1, Math.floor((t - SLOT0) / SLOT))) : Math.min(4, Math.floor(clamp01((t - 0.6) / 2.2) * 5));
  const chart = prog(t, 2.9, 0.5, ease.outCubic);
  const fix = prog(t, 4.3, 0.9, ease.inOutCubic);
  const done = prog(t, 5.3, 0.45, ease.outBack);
  const switches = real ? MIC_MODELS.map((_, i) => SLOT0 + i * SLOT) : MICS.map((_, i) => 0.6 + i * 0.44);
  return (
    <Scene t={t} n={2} label="Ваш микрофон" back="звук">
      {real && MIC_MODELS.map(([id], i) => i === sel && (
        <Sequence key={id} from={Math.round(switches[i] * PROMO_FPS)} layout="none">
          <Hero3D dir={`mics3d/${id}`} meta={mics[id] ?? null} style={{ left: 90, top: 160, width: 620, height: 775 }} fadeIn={0.08} />
        </Sequence>
      ))}
      <div style={abs(real ? { left: 760, top: 905, display: "flex", flexDirection: "row", gap: 10 } : { left: 110, top: 230, display: "flex", flexDirection: "column", gap: 20 })}>
        {(real ? MIC_MODELS.map(([, name]) => ["", name] as [string, string]) : MICS).map(([ic, label], i) => {
          const p = prog(t, 0.1 + i * 0.07, 0.4, ease.outBack);
          const on = i === sel;
          return (
            <div key={label} style={{ display: "flex", alignItems: "center", gap: real ? 0 : 22, width: real ? undefined : 520, padding: real ? "10px 16px" : "18px 26px", borderRadius: 26, background: on ? th.solid : th.chip,
              border: on ? "none" : `2px solid ${th.chipBorder}`, opacity: clamp01(p * 2), transform: `translateX(${(1 - p) * -40}px)` }}>
              {ic && <Icon d={IC[ic]} size={58} color={on ? th.onSolid : th.ink} />}
              <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: real ? 25 : 38, color: on ? th.onSolid : th.ink, whiteSpace: "nowrap" }}>{label}</div>
            </div>
          );
        })}
      </div>
      <Card p={chart} style={{ left: 760, top: 230, width: 1050, height: 640, padding: "40px 50px" }}>
        <div style={{ fontFamily: MONO, fontSize: 28, color: th.muted }}>voice_master.py analyze проба.wav</div>
        <div style={{ position: "relative", height: 380, marginTop: 30 }}>
          <div style={abs({ left: 0, right: 0, top: 190, height: 3, background: th.track })} />
          {BANDS.map((b, i) => {
            const v = DEV[i] * lerp(1, 0.18, fix) * prog(t, 3.0 + i * 0.06, 0.5, ease.outCubic);
            const h = Math.abs(v) * 36;
            return (
              <div key={String(b)} style={abs({ left: 20 + i * 135, width: 86, top: 0, height: 380 })}>
                <div style={abs({ left: 0, width: 86, top: v > 0 ? 190 - h : 193, height: h, borderRadius: 14, background: Math.abs(DEV[i]) > 2 && fix < 0.5 ? RED : th.accent })} />
                <div style={abs({ left: 0, width: 86, top: 400, textAlign: "center", fontFamily: FONT, fontWeight: 650, fontSize: 26, color: th.muted })}>{b}</div>
              </div>
            );
          })}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16, marginTop: 70, opacity: clamp01(done * 2), transform: `scale(${lerp(0.85, 1, done)})`, transformOrigin: "0 50%" }}>
          <Tick /><div style={{ fontFamily: FONT, fontWeight: 750, fontSize: 40, color: th.ink }}>пресет под ваш микрофон</div>
        </div>
      </Card>
      {switches.map((at, i) => <S key={i} at={at} f={real ? "tap" : "tick"} db={-20} />)}
      <S at={2.9} f="in" db={-16} /><S at={4.3} f="rise" db={-18} /><S at={5.3} f="success" />
    </Scene>
  );
};

// ---------------------------------------------------------------- 5. agent: a request, then the pauses collapse
const ASK = "вот дубли, смонтируй вертикальный ролик";
const CLIPS = [[0, 2.4, 0], [3.2, 5.6, 1], [6.9, 8.0, 0], [8.6, 11.4, 2]]; // [a, b, take] on a 12 s source
const Bubble: React.FC<{ t: number; at: number; text: string; top: number }> = ({ t, at, text, top }) => {
  const p = prog(t, at, 0.45, ease.outBack);
  const n = typed(t, at + 0.3, text, 30, 7);
  return (
    <div style={abs({ left: 810, top, width: 1000, display: "flex", justifyContent: "flex-end", opacity: clamp01(p * 2), transform: `scale(${lerp(0.9, 1, p)})`, transformOrigin: "100% 50%" })}>
      <div style={{ padding: "28px 40px", borderRadius: "40px 40px 10px 40px", background: ACCENT, color: "#fff", fontFamily: FONT, fontWeight: 650, fontSize: 44, boxShadow: "0 20px 50px rgba(91,140,255,0.35)" }}>{text.slice(0, n) || " "}</div>
    </div>
  );
};
const Agent: React.FC = () => {
  const t = useT();
  const th = useTheme();
  const tl = prog(t, 2.2, 0.5, ease.outCubic);
  const cut = prog(t, 3.6, 1.1, ease.inOutCubic);
  const scale = 1300 / 12;
  let packed = 0;
  return (
    <Scene t={t} n={3} label="Агент монтирует" back="монтаж">
      <Bubble t={t} at={0.2} text={ASK} top={200} />
      <Card p={tl} style={{ left: 260, top: 450, width: 1400, height: 430, padding: "40px 50px" }}>
        <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 30, color: th.muted }}>паузы режутся только в измеренной тишине</div>
        <div style={{ position: "relative", height: 120, marginTop: 50, borderRadius: 18, background: th.track }}>
          {CLIPS.map(([a, b, k], i) => {
            const el = <div key={i} style={abs({ left: lerp(a * scale, packed, cut), top: 12, width: (b - a) * scale - 6, height: 96, borderRadius: 14, background: (th.name === "cine" ? ["#8EA3C8", "#5F7398", th.accent] : ["#2A3140", "#4A5A7A", th.accent])[k] })} />;
            packed += (b - a) * scale;
            return el;
          })}
          {CLIPS.slice(0, -1).map(([, b], i) => (
            <div key={`p${i}`} style={abs({ left: b * scale, top: 12, width: (CLIPS[i + 1][0] - b) * scale - 6, height: 96, borderRadius: 14, opacity: 1 - cut,
              background: "repeating-linear-gradient(135deg, rgba(229,72,77,0.35) 0 10px, rgba(229,72,77,0.12) 10px 20px)" })} />
          ))}
        </div>
        <div style={{ display: "flex", gap: 30, marginTop: 44, fontFamily: FONT, fontSize: 32, fontWeight: 650 }}>
          <span style={{ color: th.ink, opacity: prog(t, 4.8, 0.4) }}>12.0 с → {CLIPS.reduce((s, [a, b]) => s + b - a, 0).toFixed(1)} с</span>
          <span style={{ color: GREEN, opacity: prog(t, 5.2, 0.4) }}>✓ лучший дубль по тексту</span>
          <span style={{ color: GREEN, opacity: prog(t, 5.6, 0.4) }}>✓ 0 флагов</span>
        </div>
      </Card>
      <S at={0.2} f="tap" /><S at={2.2} f="in" db={-16} /><S at={3.6} f="whoosh" db={-16} /><S at={4.7} f="land" />
    </Scene>
  );
};

// ---------------------------------------------------------------- 6. QC: findings count down to zero, loudness lands on −15
const ROWS: [string, number][] = [["паузы", 7], ["застывший экран", 3], ["вспышки", 2], ["фантомные кадры", 10], ["скачки громкости", 4]];
const Qc: React.FC = () => {
  const t = useT();
  const th = useTheme();
  const meter = prog(t, 3.4, 1.4, ease.inOutCubic);
  const lufs = lerp(-27, -15, meter);
  return (
    <Scene t={t} n={4} label="Проверка" back="проверка">
      <Card p={prog(t, 0.2, 0.5, ease.outCubic)} style={{ left: 160, top: 220, width: 980, height: 680, padding: "44px 56px" }}>
        {ROWS.map(([label, v], i) => {
          const left = Math.round(v * (1 - prog(t, 0.9 + i * 0.32, 0.8, ease.inOutCubic)));
          return (
            <div key={label} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", height: 116, borderBottom: i < 4 ? `2px solid ${th.track}` : "none", fontFamily: FONT }}>
              <span style={{ fontWeight: 700, fontSize: 42, color: th.ink }}>{label}</span>
              <span style={{ display: "flex", alignItems: "center", gap: 20 }}>
                <span style={{ fontWeight: 850, fontSize: 50, color: left ? RED : GREEN, minWidth: 60, textAlign: "right" }}>{left}</span>
                {left ? <span style={{ width: 46, height: 46, borderRadius: 99, background: th.track }} /> : <Tick />}
              </span>
            </div>
          );
        })}
      </Card>
      <Card p={prog(t, 3.2, 0.5, ease.outCubic)} style={{ left: 1200, top: 220, width: 560, height: 680, padding: "44px 50px", display: "flex", flexDirection: "column", alignItems: "center" }}>
        <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 34, color: th.muted }}>громкость</div>
        <div style={{ position: "relative", width: 120, height: 400, marginTop: 34, borderRadius: 30, background: th.track, overflow: "hidden" }}>
          <div style={abs({ left: 0, bottom: 0, width: 120, height: `${((lufs + 30) / 18) * 100}%`, background: `linear-gradient(0deg, ${th.accent}, #8FB0FF)` })} />
          <div style={abs({ left: 0, width: 120, bottom: `${(15 / 18) * 100}%`, height: 4, background: th.ink })} />
        </div>
        <div style={{ fontFamily: FONT, fontWeight: 850, fontSize: 64, color: meter >= 1 ? GREEN : th.ink, marginTop: 30 }}>{lufs.toFixed(0)} LUFS</div>
      </Card>
      {ROWS.map((_, i) => <S key={i} at={1.6 + i * 0.32} f="tick" db={-20} />)}
      <S at={3.2} f="in" db={-16} /><S at={4.8} f="success" />
    </Scene>
  );
};

// ---------------------------------------------------------------- 7. styles: the same card light and cine; the agent restyles it on request
const MiniCard: React.FC<{ t: number; accent: string; title: string }> = ({ t, accent, title }) => {
  const th = useTheme();
  const bars: [string, number][] = [["монтаж", 0.92], ["звук", 0.78], ["проверка", 1]];
  return (
    <div style={{ width: 640, height: 470, borderRadius: 40, overflow: "hidden", position: "relative",
      boxShadow: th.name === "cine" ? `0 30px 90px rgba(0,0,0,0.6), 0 0 70px ${accent}55` : "0 30px 80px rgba(0,0,0,0.35)", border: th.name === "cine" ? "2px solid rgba(170,200,255,0.45)" : "none" }}>
      <th.Bg t={t} />
      <div style={abs({ left: 50, top: 44, fontFamily: FONT, fontWeight: 750, fontSize: 36, color: th.ink })}>{title}</div>
      <div style={abs({ left: 50, top: 120, width: 540, padding: "34px 38px", borderRadius: 28, ...th.card })}>
        {bars.map(([l, v], i) => {
          const p = prog(t, 0.5 + i * 0.2, 0.9, ease.inOutCubic);
          return (
            <div key={l} style={{ marginTop: i ? 26 : 0 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontFamily: FONT, fontWeight: 700, fontSize: 28, color: th.ink, marginBottom: 10 }}><span>{l}</span><span style={{ color: accent }}>{Math.round(v * 100 * p)} %</span></div>
              <div style={{ height: 16, borderRadius: 99, background: th.track }}><div style={{ height: 16, width: `${v * 100 * p}%`, borderRadius: 99, background: accent }} /></div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
const mixHex = (a: string, b: string, p: number) => {
  const c = (h: string) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const [x, y] = [c(a), c(b)];
  return `#${x.map((v, i) => Math.round(lerp(v, y[i], p)).toString(16).padStart(2, "0")).join("")}`;
};
const Styles: React.FC = () => {
  const t = useT();
  const th = useTheme();
  const ASK2 = "сделай акцент зелёным";
  const recolor = prog(t, 4.6, 0.8, ease.inOutCubic);
  const accent = mixHex(ACCENT, "#2FB36B", recolor);
  const l = prog(t, 0.2, 0.5, ease.outCubic), r = prog(t, 0.5, 0.5, ease.outCubic);
  const note = prog(t, 5.6, 0.5, ease.outCubic);
  return (
    <Scene t={t} label="Стили анимации">
      <div style={abs({ left: 260, top: 370, ...rise(l) })}><KitTheme name="light"><MiniCard t={t} accent={accent} title="светлый" /></KitTheme></div>
      <div style={abs({ left: 1020, top: 370, ...rise(r) })}><KitTheme name="cine"><MiniCard t={t} accent={accent} title="кино" /></KitTheme></div>
      <Bubble t={t} at={2.0} text={ASK2} top={200} />
      <div style={abs({ left: 0, width: W, top: 900, textAlign: "center", fontFamily: FONT, fontWeight: 750, fontSize: 46, color: th.ink, ...rise(note) })}>
        любой вариант меняется <span style={{ color: th.accent }}>словами через агента</span>
      </div>
      <S at={0.2} f="in" db={-16} /><S at={0.5} f="in" db={-18} /><S at={2.0} f="tap" /><S at={4.6} f="glint" /><S at={5.6} f="land" />
    </Scene>
  );
};

// ---------------------------------------------------------------- 8. limits: draft → your notes → final
const Limits: React.FC = () => {
  const t = useT();
  const th = useTheme();
  const steps: [string, string, boolean][] = [["play", "черновик 720p", false], ["user", "ваши замечания", true], ["check", "финал 1440p", false]];
  return (
    <Scene t={t} label="Чего ИИ не умеет" back="вкус">
      <div style={abs({ left: 0, width: W, top: 330, display: "flex", justifyContent: "center", alignItems: "center", gap: 40 })}>
        {steps.map(([ic, label, you], i) => {
          const p = prog(t, 0.4 + i * 0.6, 0.5, ease.outBack);
          return (
            <React.Fragment key={label}>
              {i > 0 && <div style={{ width: 90, height: 8, borderRadius: 4, background: `linear-gradient(90deg, ${th.muted} ${prog(t, 0.2 + i * 0.6, 0.4) * 100}%, transparent 0)` }} />}
              <div style={{ width: 400, height: 400, borderRadius: 48, ...(you ? { background: th.solid, boxShadow: th.card.boxShadow } : th.card), display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 34,
                opacity: clamp01(p * 2), transform: `translateY(${(1 - p) * 40}px) scale(${lerp(0.85, 1, p) * (you ? 1.06 : 1)})` }}>
                <Icon d={IC[ic]} size={130} color={you ? th.onSolid : th.ink} />
                <div style={{ fontFamily: FONT, fontWeight: 750, fontSize: 42, color: you ? th.onSolid : th.ink }}>{label}</div>
              </div>
            </React.Fragment>
          );
        })}
      </div>
      <div style={abs({ left: 0, width: W, top: 820, textAlign: "center", fontFamily: FONT, fontWeight: 750, fontSize: 52, color: th.ink, ...rise(prog(t, 2.4, 0.5)) })}>
        вкус и финальное ухо - <span style={{ color: th.accent }}>ваши</span>
      </div>
      {[0, 1, 2].map((i) => <S key={i} at={0.4 + i * 0.6} f={i === 1 ? "glint" : "tap"} db={-16} />)}
    </Scene>
  );
};

// ---------------------------------------------------------------- 9. CTA: the kit, MIT, where to get it
const Cta: React.FC<{ dur: number }> = ({ dur }) => {
  const t = useT();
  const th = useTheme();
  const title = prog(t, 0.1, 0.6, ease.outExpo);
  const pill = prog(t, 1.1, 0.5, ease.outBack);
  const out = prog(t, dur - 0.6, 0.6, ease.inCubic);
  const hero = useHero("case");
  const col: React.CSSProperties = hero ? { left: 800, width: 1040, justifyContent: "flex-start", textAlign: "left" } : { left: 0, width: W, justifyContent: "center", textAlign: "center" };
  return (
    <AbsoluteFill style={{ opacity: 1 - out, background: "#000" }}>
      <Scene t={t}>
        {hero && <Hero3D dir="promo3d/case" meta={hero} style={{ left: 10, top: 150, width: 820, height: 820 }} fadeIn={0.1} />}
        <div style={abs({ ...col, top: hero ? 270 : 240, fontFamily: FONT, fontWeight: 850, fontSize: hero ? 128 : 150, letterSpacing: "-0.045em", color: th.ink, whiteSpace: "nowrap", ...rise(title, 40) })}>
          Reinh <span style={{ color: th.accent }}>Edit Kit</span>
        </div>
        <div style={abs({ ...col, top: hero ? 450 : 460, display: "flex", gap: 18 })}>
          {["MIT", "бесплатно", "macOS · Linux · WSL"].map((c, i) => <Chip key={c} text={c} p={prog(t, 0.5 + i * 0.12, 0.4, ease.outBack)} size={38} />)}
        </div>
        <div style={abs({ ...col, top: hero ? 600 : 640, display: "flex", opacity: clamp01(pill * 2), transform: `scale(${lerp(0.9, 1, pill)})`, transformOrigin: hero ? "0 50%" : "50% 50%" })}>
          <div style={{ display: "flex", alignItems: "center", gap: 26, padding: "26px 52px 26px 30px", borderRadius: 999, background: th.name === "cine" ? "rgba(255,255,255,0.96)" : "rgba(17,19,24,0.94)", boxShadow: th.card.boxShadow }}>
            <div style={{ width: 84, height: 84, borderRadius: 99, background: ACCENT, display: "flex", alignItems: "center", justifyContent: "center" }}><Icon d={IC.send} size={46} color="#fff" sw={2.1} /></div>
            <div>
              <div style={{ fontFamily: FONT, fontWeight: 800, fontSize: 56, color: th.name === "cine" ? "#111318" : "#fff" }}>t.me/reinhworks</div>
              <div style={{ fontFamily: FONT, fontWeight: 550, fontSize: 32, color: th.name === "cine" ? "#5B6170" : "rgba(255,255,255,0.65)" }}>ссылка на GitHub - в канале</div>
            </div>
          </div>
        </div>
        <S at={0.1} f="chapter" db={-14} /><S at={1.1} f="land" />
        {hero && <><S at={0.9} f="in" db={-16} /><S at={1.7} f="glint" db={-14} />{[0, 1, 2].map((i) => <S key={i} at={1.75 + i * 0.18} f="tap" db={-18} />)}</>}
      </Scene>
    </AbsoluteFill>
  );
};

const SCENES: Record<SceneId, React.FC<{ dur: number }>> = { hook: Hook, pipeline: Pipeline, install: Install, mic: Mic, agent: Agent, qc: Qc, styles: Styles, limits: Limits, cta: Cta };

export const Promo: React.FC<PromoProps> = ({ vo, variant = "mix", heroes = {} }) => {
  loadBaseFonts();
  const frame = useCurrentFrame();
  const t = frame / PROMO_FPS;
  const durs = sceneDurations(vo);
  const starts = durs.map((_, i) => durs.slice(0, i).reduce((a, b) => a + b, 0));
  return (
    <HeroCtx.Provider value={heroes}>
    <AbsoluteFill style={{ background: "#000" }}>
      {script.scenes.map((s, i) => {
        const Scene = SCENES[s.id as SceneId];
        const name = themeOf(variant, s.id);
        return (
          <Sequence key={s.id} from={Math.round(starts[i] * PROMO_FPS)} durationInFrames={Math.round(durs[i] * PROMO_FPS)} name={`${s.id} · ${name}`}>
            <KitTheme name={name}><Fit><Scene dur={durs[i]} /></Fit></KitTheme>
            {vo?.[s.id] ? <Sequence from={Math.round(0.35 * PROMO_FPS)} layout="none"><Audio src={staticFile(`promo/vo_${s.id}.wav`)} /></Sequence> : null}
          </Sequence>
        );
      })}
      {/* one light leak on every scene change: soft between two cine scenes, full where light meets dark (covers the jump) */}
      {starts.slice(1).map((at, i) => <LightLeak key={i} t={t} at={at} seed={i} dark={themeOf(variant, script.scenes[i].id) === "cine" && themeOf(variant, script.scenes[i + 1].id) === "cine"} />)}
      {starts.slice(1).map((at, i) => <S key={`w${i}`} at={at - 0.12} f="whoosh" db={-24} />)}
    </AbsoluteFill>
    </HeroCtx.Provider>
  );
};

export const PROMO_VARIANTS: PromoVariant[] = ["mix", "light", "cine"];
export { THEMES };

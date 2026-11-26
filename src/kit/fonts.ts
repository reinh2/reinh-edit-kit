// Base fonts: Inter (variable 100–900) and JetBrains Mono, both SIL OFL 1.1 (public/fonts/*-OFL.txt), served from
// public/fonts, Cyrillic + Latin subsets. Another font: put its woff2 + licence into public/fonts and add it here.
import { cancelRender, continueRender, delayRender, staticFile } from "remotion";

const CYR = "U+0301, U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116";
const LAT =
  "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD";

const faces: [string, string, string, string][] = [
  ["Inter", "fonts/inter-cyrillic.woff2", CYR, "100 900"],
  ["Inter", "fonts/inter-latin.woff2", LAT, "100 900"],
  ["JetBrains Mono", "fonts/jbmono-cyrillic.woff2", CYR, "400"],
  ["JetBrains Mono", "fonts/jbmono-latin.woff2", LAT, "400"],
];

// Called on first render (not at import: while Remotion lists compositions the public dir is not served yet).
let loading = false;
export const loadBaseFonts = () => {
  if (loading || typeof document === "undefined") return;
  loading = true;
  const handle = delayRender("base fonts");
  Promise.all(
    faces.map(([family, file, unicodeRange, weight]) =>
      new FontFace(family, `url(${staticFile(file)}) format('woff2')`, { unicodeRange, weight }).load().then((f) => document.fonts.add(f)),
    ),
  )
    .then(() => continueRender(handle))
    .catch((e) => cancelRender(e));
};

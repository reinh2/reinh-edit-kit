import React from "react";
import { Composition, staticFile } from "remotion";
import { EndCard } from "./kit/EndCard";
import { Example, exampleDuration, type ExampleProps } from "./example/Example";
import { SampleScreen } from "./example/SampleScreen";
import { KIT } from "./kit/theme";
import { HERO_NAMES, MIC_MODELS, Promo, PROMO_FPS, PROMO_VARIANTS, promoFrames, type PromoHeroes, type PromoProps } from "./promo/Promo";
import { loadHeroMeta } from "./kit/Hero3D";

// Drafts: render at a smaller scale instead of separate compositions, e.g. `--scale=0.6666666666666666` → 1280×720 from 1920×1080.
const loadExample = async () => {
  const r = await fetch(staticFile("example/meta.json"));
  if (!r.ok) throw new Error("public/example/meta.json is missing: run `npm run sample` first");
  return (await r.json()) as ExampleProps;
};

export const RemotionRoot: React.FC = () => {
  const S = KIT.formats.short;
  return (
    <>
      <Composition id="SampleScreen" component={SampleScreen} durationInFrames={330} fps={30} width={1920} height={1080} />
      <Composition id="Example" component={Example} fps={30} width={1920} height={1080} defaultProps={{ words: [], voiceDur: 10 } as ExampleProps}
        calculateMetadata={async () => { const props = await loadExample(); return { props, durationInFrames: Math.round(exampleDuration(props) * 30) }; }} />
      <Composition id="ExampleShort" component={Example} fps={S.fps} width={S.width} height={S.height} defaultProps={{ words: [], voiceDur: 10, vertical: true }}
        calculateMetadata={async () => { const props = await loadExample(); return { props: { ...props, vertical: true }, durationInFrames: Math.round(exampleDuration(props) * S.fps) }; }} />
      <Composition id="EndCard" component={EndCard} durationInFrames={90} fps={30} width={1920} height={1080} defaultProps={{ dur: 3 }} />
      <Composition id="EndCardShort" component={EndCard} durationInFrames={90} fps={30} width={1080} height={1920} defaultProps={{ dur: 3 }} />
      {PROMO_VARIANTS.map((variant) => (
        <Composition key={variant} id={variant === "mix" ? "Promo" : `Promo-${variant === "light" ? "Light" : "Cine"}`} component={Promo} fps={PROMO_FPS} width={2560} height={1440}
          defaultProps={{ vo: null, variant } as PromoProps} durationInFrames={promoFrames(null)}
          calculateMetadata={async ({ props }) => {
            // scratch voice-over (npm run promo:vo) sets the scene lengths; without it the promo renders silent at minimum lengths
            const r = await fetch(staticFile("promo/vo.json")).catch(() => null);
            const vo = r && r.ok ? ((await r.json()) as Record<string, number>) : null;
            // 3D heroes (npm run promo:3d): missing renders → the flat layout of each scene
            const heroes: PromoHeroes = Object.fromEntries(await Promise.all(HERO_NAMES.map(async (n) => [n, await loadHeroMeta(`promo3d/${n}`)] as const)));
            heroes.mics = Object.fromEntries(await Promise.all(MIC_MODELS.map(async ([id]) => [id, await loadHeroMeta(`mics3d/${id}`)] as const)));
            return { props: { ...props, vo, heroes }, durationInFrames: promoFrames(vo) };
          }} />
      ))}
    </>
  );
};

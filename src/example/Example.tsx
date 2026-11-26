// The starter example: what a finished edit is made of, on synthetic material (`npm run sample` makes it).
//   Example       16:9 — «face» plate with an overlay card on a word, the screen recording framed by ScreenCam, end card;
//   ExampleShort  9:16 — the same with word captions.
// Replace the plate with your camera file (OffthreadVideo) and the sample with your EDL timeline when you edit for real.
import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile, useVideoConfig } from "remotion";
import { Bar, OverlayCard, Pill } from "../kit/Card";
import { Captions } from "../kit/Captions";
import { EndCard } from "../kit/EndCard";
import { loadBaseFonts } from "../kit/fonts";
import { ScreenCam, type CamKey } from "../kit/ScreenCam";
import { Sfx } from "../kit/sfx";
import { C, FONT } from "../kit/theme";
import { T, type Word } from "../kit/words";

export type ExampleProps = { words: Word[]; voiceDur: number };
export const FACE_END = 4.2;
export const SCREEN_DUR = 9;
export const END = 3;
export const exampleDuration = (p: ExampleProps) => Math.max(FACE_END + SCREEN_DUR, p.voiceDur + 0.5) + END;

// A stand-in for your camera: never someone's face in a public example.
const Plate: React.FC = () => (
  <AbsoluteFill style={{ background: "radial-gradient(80% 80% at 50% 40%, #39404F 0%, #1C2029 70%)", alignItems: "center", justifyContent: "center" }}>
    <svg width="22%" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.35)" strokeWidth={1.2}>
      <path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M4.5 20a7.5 7.5 0 0 1 15 0" />
    </svg>
    <div style={{ fontFamily: FONT, fontSize: 34, color: "rgba(255,255,255,0.5)", marginTop: 20 }}>здесь ваше видео с камеры</div>
  </AbsoluteFill>
);

const CAMS: CamKey[] = [[0, 960, 540, 1920, 0], [0.6, 640, 330, 1100, 0.8], [3.4, 640, 520, 1100, 0.7], [6.4, 960, 540, 1920, 0.7]];

export const Example: React.FC<ExampleProps & { vertical?: boolean }> = ({ words, voiceDur, vertical }) => {
  loadBaseFonts();
  const { fps, width } = useVideoConfig();
  const f = (s: number) => Math.round(s * fps);
  const main = Math.max(FACE_END + SCREEN_DUR, voiceDur + 0.5);
  const at = T(words, "лицо"); // the card lands on the spoken word
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <Sequence durationInFrames={f(FACE_END)}>
        <Plate />
        <OverlayCard at={at} until={FACE_END} style={vertical ? { left: 140, top: 200, width: 800 } : { left: 120, top: 110, width: 700 }}>
          <div style={{ fontSize: 30, fontWeight: 650, color: C.muted, marginBottom: 18 }}>Проверка монтажа</div>
          <Bar label="Склейки без пауз" value={100} max={100} unit=" %" at={at + 0.2} width={vertical ? 730 : 630} />
          <div style={{ height: 22 }} />
          <Bar label="Флаги длины планов" value={0} max={10} at={at + 0.4} color={C.green} width={vertical ? 730 : 630} />
        </OverlayCard>
        <Sfx at={at} ev="tap" />
      </Sequence>
      <Sequence from={f(FACE_END)} durationInFrames={f(main - FACE_END)}>
        {vertical ? (
          <AbsoluteFill style={{ background: "#14171D" }}>
            <div style={{ position: "absolute", left: 40, top: 360, width: width - 80, height: (width - 80) * 9 / 16, borderRadius: 28, overflow: "hidden", boxShadow: "0 30px 80px rgba(0,0,0,0.5)" }}>
              <ScreenCam src={staticFile("example/screen.mp4")} keys={CAMS} boxW={width - 80} boxH={(width - 80) * 9 / 16} />
            </div>
          </AbsoluteFill>
        ) : (
          <ScreenCam src={staticFile("example/screen.mp4")} keys={CAMS} blur={[[1300, 130, 300, 40]]} />
        )}
        <div style={{ position: "absolute", left: 0, right: 0, top: vertical ? 1120 : 960, display: "flex", justifyContent: "center", gap: 18 }}>
          <Pill text="монтаж" at={0.8} /><Pill text="звук" at={3.6} /><Pill text="проверка" at={6.6} hot />
        </div>
        <Sfx at={0} ev="scene-in" /><Sfx at={0.8} ev="pop" /><Sfx at={3.6} ev="pop" n={1} /><Sfx at={6.6} ev="confirm" />
      </Sequence>
      {vertical && <Captions words={words} />}
      <Sequence from={f(main)} durationInFrames={f(END)}><EndCard dur={END} /></Sequence>
      <Audio src={staticFile("example/voice.wav")} />
    </AbsoluteFill>
  );
};

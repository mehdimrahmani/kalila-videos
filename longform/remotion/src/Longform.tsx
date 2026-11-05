import React, {useState} from 'react';
import {AbsoluteFill, Audio, Img, staticFile, useCurrentFrame, useVideoConfig, interpolate, Easing, delayRender, continueRender, random} from 'remotion';

// ---------------------------------------------------------------- palette (the page's manuscript look)
const INK = '#26160e', SEPIA = '#5c3c22', LAPIS = '#1a3068', GOLD = '#d4aa5c', GOLD_HI = '#ffe8aa';

// ---------------------------------------------------------------- fonts
const useFonts = () => {
  const [handle] = useState(() => delayRender('fonts'));
  React.useEffect(() => {
    const faces = [
      new FontFace('Nasta', `url(${staticFile('common/NotoNastaliqUrdu-Regular.woff2')})`),
      new FontFace('Serif', `url(${staticFile('common/FreeSerif.ttf')})`),
      new FontFace('SerifI', `url(${staticFile('common/FreeSerifItalic.ttf')})`),
    ];
    Promise.all(faces.map((f) => f.load())).then((fs) => { fs.forEach((f) => (document as any).fonts.add(f)); continueRender(handle); });
  }, [handle]);
};

const ease = (t: number, a: number, b: number) => interpolate(t, [a, b], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic)});
const vis = (t: number, t0: number, t1: number, fin = 0.6, fout = 0.6) => ease(t, t0 - fin, t0) * (1 - ease(t, t1, t1 + fout));

// ---------------------------------------------------------------- shamsa (sun medallion)
const Shamsa: React.FC<{t: number; glow: number; size: number}> = ({t, glow, size}) => {
  const rays = 32, c = 100;
  const pts: string[] = [];
  for (let k = 0; k < rays * 2; k++) {
    const a = t * 0.05 + (k * Math.PI) / rays, r = k % 2 === 0 ? 98 : 70;
    pts.push(`${c + r * Math.cos(a)},${c + r * Math.sin(a)}`);
  }
  const inner: string[] = [];
  for (let k = 0; k < 32; k++) {
    const a = -t * 0.075 + (k * Math.PI) / 16, r = k % 2 === 0 ? 66 : 56;
    inner.push(`${c + r * Math.cos(a)},${c + r * Math.sin(a)}`);
  }
  const dots = Array.from({length: 12}, (_, k) => {
    const a = t * 0.1 + (k * Math.PI) / 6;
    return <circle key={k} cx={c + 27 * Math.cos(a)} cy={c + 27 * Math.sin(a)} r={7} fill="url(#g)" />;
  });
  const sweep = ((t * 0.22) % 2.4) - 0.2;
  return (
    <svg width={size} height={size} viewBox="0 0 200 200" style={{filter: `drop-shadow(0 0 ${8 + 22 * glow}px rgba(255,214,140,${0.25 + 0.45 * glow}))`}}>
      <defs>
        <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor={GOLD_HI} />
          <stop offset={Math.max(0, Math.min(1, sweep - 0.08))} stopColor={GOLD} />
          <stop offset={Math.max(0, Math.min(1, sweep))} stopColor={GOLD_HI} />
          <stop offset={Math.max(0, Math.min(1, sweep + 0.08))} stopColor={GOLD} />
          <stop offset="1" stopColor="#a8803e" />
        </linearGradient>
      </defs>
      <polygon points={pts.join(' ')} fill="url(#g)" />
      <polygon points={inner.join(' ')} fill={LAPIS} />
      <circle cx={c} cy={c} r={47} fill={LAPIS} stroke="url(#g)" strokeWidth={3} />
      {dots}
      <circle cx={c} cy={c} r={10} fill="url(#g)" />
    </svg>
  );
};

// ---------------------------------------------------------------- dust in the candle light
const Dust: React.FC<{t: number}> = ({t}) => (
  <AbsoluteFill style={{pointerEvents: 'none'}}>
    {Array.from({length: 70}, (_, i) => {
      const x0 = random(`x${i}`) * 1920, y0 = random(`y${i}`) * 1080, vx = (random(`vx${i}`) - 0.5) * 10, vy = -3 - random(`vy${i}`) * 10;
      const s = 1.5 + random(`s${i}`) * 3;
      const x = (((x0 + vx * t) % 1920) + 1920) % 1920, y = (((y0 + vy * t) % 1080) + 1080) % 1080;
      const tw = 0.35 + 0.35 * Math.sin(t * (0.6 + random(`f${i}`)) + i);
      return <div key={i} style={{position: 'absolute', left: x, top: y, width: s, height: s, borderRadius: '50%',
        background: 'rgba(255,236,190,1)', opacity: tw, filter: 'blur(1px)'}} />;
    })}
  </AbsoluteFill>
);

// ---------------------------------------------------------------- text helpers
const Fa: React.FC<{text: string; t: number; t0: number; reveal?: number; size?: number; color?: string; alpha?: number}> =
  ({text, t, t0, reveal = 2.2, size = 92, color = INK, alpha = 1}) => {
  const words = text.split(' ');
  return (
    <div style={{direction: 'rtl', fontFamily: 'Nasta', fontSize: size, color, lineHeight: 2.0, textAlign: 'center', opacity: alpha,
      textShadow: '0 0 1px rgba(38,22,14,0.35)'}}>
      {words.map((w, i) => {
        const a = ease(t, t0 + (i / words.length) * reveal, t0 + (i / words.length) * reveal + 0.5);
        return <span key={i} style={{opacity: a, filter: `blur(${(1 - a) * 6}px)`, display: 'inline-block', margin: '0 0.12em'}}>{w}</span>;
      })}
    </div>
  );
};
const En: React.FC<{text: string; size?: number; color?: string; alpha?: number; italic?: boolean; maxW?: number}> =
  ({text, size = 46, color = SEPIA, alpha = 1, italic = true, maxW = 1200}) => (
  <div style={{fontFamily: italic ? 'SerifI' : 'Serif', fontSize: size, color, opacity: alpha, textAlign: 'center', maxWidth: maxW,
    lineHeight: 1.35, margin: '0 auto'}}>{text}</div>
);
const ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X'];

// ---------------------------------------------------------------- the scene
export const Longform: React.FC<{id: string; timeline: any}> = ({id, timeline}) => {
  useFonts();
  const f = useCurrentFrame(); const {fps} = useVideoConfig(); const t = f / fps;
  const ev: any[] = timeline.events; const D = timeline.duration;
  const title = ev[0];
  const lines = ev.filter((e) => e.kind === 'line');
  const tafsir = ev.filter((e) => e.kind === 'tafsir');
  const chapters = ev.filter((e) => e.kind === 'chapter');
  const breaths = ev.filter((e) => e.kind === 'breath');
  const intro = ev.filter((e) => e.kind === 'intro');
  const outro = ev.filter((e) => e.kind === 'outro');
  const end = ev.find((e) => e.kind === 'end');
  // which poem are we in (for the source line and the tafsir glow)
  const ch = [...chapters].reverse().find((c) => t >= c.t0);
  const curTaf = tafsir.find((e, i) => t >= e.t0 - 0.3 && t < (tafsir[i + 1] && tafsir[i + 1].poem === e.poem ? tafsir[i + 1].t0 - 0.1 : e.t1 + 0.8));
  const tafBlock = (() => { if (!curTaf) return 0; const ts = tafsir.filter((e) => e.poem === curTaf.poem); return vis(t, ts[0].t0 - 0.4, ts[ts.length - 1].t1 + 0.6, 0.8, 0.8); })();
  // camera: slow push-in per section + gentle drift
  const zoom = 1.0 + 0.045 * ((t % 90) / 90) + 0.01 * Math.sin(t / 13);
  const dx = 18 * Math.sin(t / 17), dy = 10 * Math.sin(t / 23);
  const flick = 0.9 + 0.06 * Math.sin(t * 2.1) + 0.03 * Math.sin(t * 5.3 + 1);
  const fade = ease(t, 0, 1.2) * (1 - ease(t, D - 2, D));

  return (
    <AbsoluteFill style={{background: '#000'}}>
      <Audio src={staticFile(`${id}/audio.wav`)} />
      <AbsoluteFill style={{opacity: fade}}>
        {/* the page, moving with the camera */}
        <AbsoluteFill style={{transform: `translate(${dx}px, ${dy}px) scale(${zoom})`}}>
          <Img src={staticFile('common/paper.jpg')} style={{position: 'absolute', left: -96, top: -54, width: 2112, height: 1188}} />
          <AbsoluteFill style={{background: `radial-gradient(ellipse 70% 75% at 50% 40%, rgba(255,226,170,${0.22 * flick}) 0%, rgba(0,0,0,0) 60%, rgba(30,15,5,0.55) 100%)`}} />
        </AbsoluteFill>
        {/* shamsa */}
        <div style={{position: 'absolute', left: 960 - 95, top: 70 + 4 * Math.sin(t / 5)}}><Shamsa t={t} glow={tafBlock} size={190} /></div>
        {/* chapter header under the shamsa */}
        {ch && t > ch.t0 + 3.5 && end && t < end.t0 &&
          <div style={{position: 'absolute', top: 278, width: '100%', textAlign: 'center', fontFamily: 'Serif', fontSize: 28, letterSpacing: 6,
            color: LAPIS, opacity: 0.85 * ease(t, ch.t0 + 3.5, ch.t0 + 4.3)}}>{ROMAN[ch.n - 1]} · {ch.name.toUpperCase()}</div>}

        {/* title + intro */}
        <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', opacity: vis(t, 0.4, title.t1, 1, 0.8), paddingTop: 140}}>
          <Fa text={title.fa} t={t} t0={0.6} size={84} />
          <En text={title.text} size={78} color={INK} italic={false} />
          <div style={{height: 14}} />
          <En text={title.sub} size={36} />
          <div style={{height: 50}} />
          {intro.map((e, i) => <div key={i} style={{position: 'absolute', bottom: 150, width: '100%', opacity: vis(t, e.t0, e.t1 + 0.3, 0.4, 0.4)}}>
            <En text={e.text} size={38} /></div>)}
        </AbsoluteFill>

        {/* chapter cards */}
        {chapters.map((c, i) => (
          <AbsoluteFill key={i} style={{justifyContent: 'center', alignItems: 'center', opacity: vis(t, c.t0 + 0.2, c.t1, 0.8, 0.8)}}>
            <div style={{fontFamily: 'Serif', fontSize: 120, color: GOLD, textShadow: '0 2px 0 rgba(90,60,20,0.4)'}}>{ROMAN[c.n - 1]}</div>
            <En text={c.name} size={72} color={INK} italic={false} />
            <div style={{height: 10}} />
            <En text={c.source} size={34} />
          </AbsoluteFill>
        ))}

        {/* verse lines: the current line big; the previous line of the same poem small above it */}
        {lines.map((l, i) => {
          const a = vis(t, l.t0, l.t1, 0.5, 0.5);
          if (a <= 0) return null;
          const prev = l.k > 0 ? lines[i - 1] : null;
          return (
            <AbsoluteFill key={i} style={{justifyContent: 'center', alignItems: 'center', paddingTop: 170, opacity: a}}>
              {prev && <div style={{opacity: 0.45, transform: 'scale(0.62)', marginBottom: -40}}>
                <Fa text={prev.fa} t={99999} t0={0} size={92} color={SEPIA} /></div>}
              <Fa text={l.fa} t={t} t0={l.t0} />
              <div style={{height: 8}} />
              <div style={{opacity: ease(t, l.en_t0 - 0.2, l.en_t0 + 0.6)}}><En text={l.en} size={50} /></div>
            </AbsoluteFill>
          );
        })}

        {/* tafsir */}
        <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', paddingTop: 170, opacity: tafBlock}}>
          <div style={{position: 'absolute', top: 360, width: '100%', textAlign: 'center'}}>
            <span style={{fontFamily: 'Nasta', fontSize: 52, color: GOLD, direction: 'rtl'}}>تفسیر</span></div>
          {tafsir.map((e, i) => {
            const nxt = tafsir[i + 1] && tafsir[i + 1].poem === e.poem ? tafsir[i + 1].t0 - 0.1 : e.t1 + 0.8;
            const a = vis(t, e.t0 - 0.1, nxt - 0.25, 0.35, 0.3);
            return a > 0 ? <div key={i} style={{position: 'absolute', top: 520, width: '100%', opacity: a,
              transform: `translateY(${(1 - a) * 12}px)`}}><En text={e.text} size={54} color={SEPIA} /></div> : null;
          })}
        </AbsoluteFill>

        {/* breath: the whole poem in Persian once more, with the music */}
        {breaths.map((b, i) => (
          <AbsoluteFill key={i} style={{justifyContent: 'center', alignItems: 'center', paddingTop: 170, opacity: vis(t, b.t0, b.t1, 1.0, 1.0)}}>
            {b.fa.map((s: string, k: number) => <Fa key={k} text={s} t={t} t0={b.t0 + k * 0.6} size={b.fa.length > 2 ? 64 : 80} color={INK} />)}
            <div style={{height: 34}} /><En text={b.source} size={32} />
          </AbsoluteFill>
        ))}

        {/* outro */}
        {end && <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', paddingTop: 150, opacity: vis(t, end.t0, D - 1.5, 0.8, 0.8)}}>
          {outro.map((e, i) => <div key={i} style={{opacity: ease(t, e.t0 - 0.2, e.t0 + 0.5)}}>
            <En text={e.text} size={i === outro.length - 1 ? 60 : 44} color={i === outro.length - 1 ? INK : SEPIA} italic={i !== outro.length - 1} />
            <div style={{height: 16}} /></div>)}
          <div style={{height: 20}} />
          <En text="@theguesthouse.poetry" size={36} color={LAPIS} italic={false} />
        </AbsoluteFill>}

        {/* source line during the verses */}
        {ch && lines.some((l) => t >= l.t0 && t <= l.t1) &&
          <div style={{position: 'absolute', bottom: 120, width: '100%', textAlign: 'center', fontFamily: 'SerifI', fontSize: 30, color: SEPIA, opacity: 0.85}}>
            {ch.source}</div>}

        <Dust t={t} />
        {/* the illuminated border stays fixed on the frame */}
        <Img src={staticFile('common/border.png')} style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080}} />
        <div style={{position: 'absolute', bottom: 62, width: '100%', textAlign: 'center', fontFamily: 'Serif', fontSize: 24, color: SEPIA, opacity: 0.7}}>
          The Guest House · Rumi from the original Persian</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

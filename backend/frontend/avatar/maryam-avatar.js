/**
 * MaryamAvatar (alias AylaAvatar) — talking 3D avatar for Səma Care (Three.js, ES module).
 *
 *   const maryam = new MaryamAvatar(containerEl, { src: "/avatar/maryam.glb" });
 *   await maryam.load();
 *   maryam.setState("idle" | "listening" | "thinking" | "speaking");
 *   maryam.setEmotion("happy" | "empathetic" | "serious" | "concerned" | "neutral", { intensity, durationMs });
 *   maryam.connectAudio(audioElement | mediaStream);        // real lipsync from audio (visemes from the spectrum)
 *   maryam.useFrequencySource(() => conversation.getOutputByteFrequencyData()); // ElevenLabs SDK (bins = 100–8000 Hz)
 *   maryam.useFrequencySource(fn, 48000) / (fn, [minHz, maxHz])                // raw AnalyserNode data / custom range
 *   maryam.stopAudio();                                   // detach audio lipsync (call ended)
 *   maryam.speakText("Salam! 10 manatı balansınıza qaytardım."); // silent, letter-accurate lipsync (chat mode)
 *   maryam.lookAt(x, y)  // optional: normalized screen point -1..1 (e.g. pointer); null to release
 *
 * GLB: body mesh morphs jawOpen, mouthSmile, mouthStretch, mouthFunnel, mouthPucker, mouthRollLower, mouthPress,
 *      browInnerUp, browDown · "MouthGap" (same mouth morphs) · "Eyelids" (eyeBlinkLeft/Right) · "EyeLeft"/"EyeRight" eyeballs.
 */
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const approach = (cur, target, rate, dt) => cur + (target - cur) * (1 - Math.exp(-rate * dt));
const rand = (a, b) => a + Math.random() * (b - a);
const DEG = Math.PI / 180;

// viseme -> morph weights (shapes from the classic Disney/Pixar chart: a/e/i, o/u/w, f/v, b/m/p, ...)
const VISEME = {
  rest: {},
  A: { jawOpen: 0.85, mouthStretch: 0.18 },                       // a, ə
  E: { jawOpen: 0.5, mouthStretch: 0.45, mouthSmile: 0.15 },     // e, i, ı
  O: { jawOpen: 0.55, mouthFunnel: 0.75 },                         // o, ö
  U: { jawOpen: 0.3, mouthPucker: 0.6, mouthFunnel: 0.35 },       // u, ü, w
  FV: { jawOpen: 0.1, mouthRollLower: 0.9 },                       // f, v
  MBP: { mouthPress: 0.85 },                                       // m, b, p (lips closed)
  C: { jawOpen: 0.25, mouthStretch: 0.12 },                        // other consonants
  S: { jawOpen: 0.12, mouthStretch: 0.35 },                        // s, z, ş, ç, c, j
};
const letterViseme = (ch) => {
  if ("aəá".includes(ch)) return "A"; if ("eiıé".includes(ch)) return "E"; if ("oö".includes(ch)) return "O";
  if ("uüw".includes(ch)) return "U"; if ("fv".includes(ch)) return "FV"; if ("mbp".includes(ch)) return "MBP";
  if ("szşçcjх".includes(ch)) return "S"; if (/[a-zğqxkgtdlnrhyЀ-ӿ]/.test(ch)) return "C";
  return null;
};
const EMOTIONS = {
  neutral: {},
  happy: { mouthSmile: 0.85, browInnerUp: 0.25 },
  empathetic: { browInnerUp: 0.85, mouthSmile: 0.2 },
  serious: { browDown: 0.6, mouthPress: 0.15 },
  concerned: { browInnerUp: 0.65, browDown: 0.25 },
};
const TAG_EMOTION = { empathetic: "empathetic", calm: "neutral", warm: "happy", reassuring: "happy", relieved: "happy",
  cheerfully: "happy", serious: "serious", softly: "empathetic", sighs: "concerned" };
const STATES = {
  idle: { head: [0, 0, 0], face: { mouthSmile: 0.18 }, blink: [2.2, 5] },
  listening: { head: [0, 2.5, 2], face: { mouthSmile: 0.28, browInnerUp: 0.12 }, blink: [2, 4.2] },
  thinking: { head: [-4, -2, 3], face: { browDown: 0.3, mouthPress: 0.25 }, blink: [3, 6] },
  speaking: { head: [0, 0.5, 0], face: { mouthSmile: 0.12 }, blink: [2.6, 5.5] },
};

export class MaryamAvatar {
  constructor(container, { src = "./maryam.glb", framing = "bust", transparent = true, pixelRatioCap = 2, followPointer = true,
                            reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false } = {}) {
    Object.assign(this, { container, src, framing });
    this.motion = reducedMotion ? 0.35 : 1;          // scales head/body motion (lipsync and blinks stay)
    this.visible = true;
    this.state = "idle";
    this.emotion = { name: "neutral", w: {}, until: Infinity };
    this.morph = {}; this.cur = {};
    this.eyes = []; this.eyelids = null;
    this.clock = new THREE.Clock();
    // speech analysis
    this.analyser = null; this.freqSource = null; this.freq = null; this.freqRange = [0, 24000];
    this.noise = 0.03; this.peak = 0.25; this.valley = 0; this.avgE = 0; this.env = 0; this.silentFor = 1; this.lastPulse = 0;
    this.viseme = "rest"; this.visW = 0;
    this.textTrack = null;
    // life
    this.blinkT = -1; this.nextBlink = 1.2; this.doubleBlink = false;
    this.gaze = { yaw: 0, pitch: 0 }; this.gazeTarget = { yaw: 0, pitch: 0 }; this.nextSaccade = 0.8; this.glanceUntil = 0;
    this.pointer = null; this.pulse = { brow: 0, nod: 0, smile: 0 };

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: transparent });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, pixelRatioCap));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping; this.renderer.toneMappingExposure = 1.05;
    container.appendChild(this.renderer.domElement); this.renderer.domElement.style.display = "block";
    this.scene = new THREE.Scene();
    this.scene.environment = new THREE.PMREMGenerator(this.renderer).fromScene(new RoomEnvironment(), 0.04).texture;
    const key = new THREE.DirectionalLight(0xfff4ee, 1.6); key.position.set(-0.8, 1.2, 1.6);
    const fill = new THREE.DirectionalLight(0xe9e2ff, 0.6); fill.position.set(1.2, 0.4, 1.2);
    const rim = new THREE.DirectionalLight(0xc4b5fd, 1.1); rim.position.set(0.2, 1.0, -1.5);
    this.scene.add(key, fill, rim, new THREE.HemisphereLight(0xffffff, 0xd8ccff, 0.35));
    this.camera = new THREE.PerspectiveCamera(22, 1, 0.01, 20);
    this.root = new THREE.Group(); this.head = new THREE.Group(); this.root.add(this.head); this.scene.add(this.root);
    this._resize = () => this.resize(); window.addEventListener("resize", this._resize);
    if (window.ResizeObserver) { this._ro = new ResizeObserver(this._resize); this._ro.observe(container); }
    if (window.IntersectionObserver) {                // stop rendering while off-screen
      this._io = new IntersectionObserver(([e]) => { this.visible = e.isIntersecting; }); this._io.observe(this.renderer.domElement);
    }
    if (followPointer) {
      this._pm = (e) => { const r = this.renderer.domElement.getBoundingClientRect();
        this.pointer = { x: ((e.clientX - r.left) / r.width) * 2 - 1, y: -(((e.clientY - r.top) / r.height) * 2 - 1), t: performance.now() }; };
      window.addEventListener("pointermove", this._pm);
    }
  }

  async load() {
    const gltf = await new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).loadAsync(this.src);
    const model = gltf.scene;
    const box = new THREE.Box3().setFromObject(model);
    const size = box.getSize(new THREE.Vector3()), center = box.getCenter(new THREE.Vector3());
    const neck = new THREE.Vector3(center.x, box.min.y + size.y * 0.42, center.z);
    this.head.position.copy(neck); model.position.sub(neck); this.head.add(model);
    model.traverse((o) => {
      if (/^Eye(Left|Right)$/.test(o.name)) this.eyes.push(o);
      if (!o.isMesh) return;
      o.frustumCulled = false;
      if (o.name === "Eyelids" || o.parent?.name === "Eyelids") { this.eyelids = o; o.visible = false; }
      for (const [name, index] of Object.entries(o.morphTargetDictionary || {})) (this.morph[name] ||= []).push({ mesh: o, index });
    });
    this.bounds = { top: box.max.y - neck.y, bottom: box.min.y - neck.y };
    this.resize();
    this.renderer.setAnimationLoop(() => this._tick());
    return this;
  }

  // ------------------------------------------------------------------ public API
  /** Move the same avatar (no GLB reload) into another container, e.g. on route change or chat → call. */
  mount(container, { framing } = {}) {
    if (framing) this.framing = framing;
    this._ro?.unobserve(this.container); this.container = container; container.appendChild(this.renderer.domElement);
    this._ro?.observe(container); this.resize();
  }
  setState(state) { if (STATES[state] && state !== this.state) { this.state = state; this.nextSaccade = 0; } }
  setEmotion(name, { intensity = 1, durationMs = 2500 } = {}) {
    const w = EMOTIONS[name] || {};
    this.emotion = { name, w: Object.fromEntries(Object.entries(w).map(([k, v]) => [k, v * intensity])),
      until: durationMs > 0 ? performance.now() + durationMs : Infinity };
  }
  reactToText(text) {
    const m = /\[([a-z]+)\]/i.exec(text || "");
    if (m && TAG_EMOTION[m[1].toLowerCase()]) this.setEmotion(TAG_EMOTION[m[1].toLowerCase()], { durationMs: 3500 });
  }
  connectAudio(source) {
    const ctx = this.audioCtx ||= new (window.AudioContext || window.webkitAudioContext)();
    const node = source instanceof MediaStream ? ctx.createMediaStreamSource(source) : (source._maryamNode ||= ctx.createMediaElementSource(source));
    this.analyser = ctx.createAnalyser(); this.analyser.fftSize = 1024; this.analyser.smoothingTimeConstant = 0.15;
    node.connect(this.analyser);
    if (!(source instanceof MediaStream)) this.analyser.connect(ctx.destination);
    this.freq = new Uint8Array(this.analyser.frequencyBinCount); this.freqRange = [0, ctx.sampleRate / 2]; this.freqSource = null;
    this.peak = 0.25; this.noise = 0.03; this.valley = 0;
    if (ctx.state === "suspended") ctx.resume();
  }
  /** range: [minHz, maxHz] of the bins; a number = sample rate of a raw AnalyserNode (0..sr/2). Default = ElevenLabs SDK (100–8000 Hz). */
  useFrequencySource(fn, range = [100, 8000]) {
    this.freqSource = fn; this.analyser = null; this.freqRange = typeof range === "number" ? [0, range / 2] : range;
    this.peak = 0.25; this.noise = 0.03; this.valley = 0;
  }
  stopAudio() { this.analyser = null; this.freqSource = null; this.viseme = "rest"; this.visW = 0; }
  lookAt(x, y) { this.pointer = x == null ? null : { x, y, t: performance.now() + 1e9 }; }

  /** Letter-accurate lipsync for chat (no audio): visemes per character, real pauses at spaces/punctuation. */
  speakText(text, charsPerSec = 14) {
    const clean = (text || "").replace(/\[[^\]]+\]/g, "").toLowerCase();
    const track = []; let t = 0; const step = 1 / charsPerSec;
    for (const ch of clean) {
      if (ch === " ") { track.push({ t, v: "rest", w: 0.25 }); t += step * 0.6; continue; }
      if (",;:".includes(ch)) { track.push({ t, v: "MBP", w: 0.5 }); t += 0.22; track.push({ t, v: "rest", w: 0, pause: true }); t += 0.12; continue; }
      if (".!?\n".includes(ch)) { track.push({ t, v: "MBP", w: 0.6 }); t += 0.25; track.push({ t, v: "rest", w: 0, pause: true, end: true }); t += 0.3; continue; }
      const v = letterViseme(ch); if (!v) continue;
      track.push({ t, v, w: v === "A" || v === "O" ? 1 : 0.85, stress: v === "A" && Math.random() < 0.25 }); t += step;
    }
    this.textTrack = { track, start: performance.now(), dur: t, i: 0 };
    this.setState("speaking");
    return new Promise((r) => setTimeout(() => { this.textTrack = null; this.setState("idle"); r(); }, t * 1000 + 120));
  }

  resize() {
    const w = this.container.clientWidth || 400, h = this.container.clientHeight || 400;
    this.renderer.setSize(w, h, false); this.camera.aspect = w / h;
    if (this.bounds) {
      const face = this.framing === "face";
      const targetY = face ? this.bounds.top * 0.55 : (this.bounds.top + this.bounds.bottom) / 2 + this.bounds.top * 0.04;
      const span = face ? this.bounds.top * 0.85 : (this.bounds.top - this.bounds.bottom) * 1.12;
      const dist = (span / 2) / Math.tan((this.camera.fov / 2) * DEG) / Math.min(1, w / h);
      this.camera.position.set(0, this.head.position.y + targetY, dist);
      this.camera.lookAt(0, this.head.position.y + targetY, 0);
    }
    this.camera.updateProjectionMatrix();
  }
  dispose() {
    this.renderer.setAnimationLoop(null); window.removeEventListener("resize", this._resize);
    if (this._pm) window.removeEventListener("pointermove", this._pm);
    this._ro?.disconnect(); this._io?.disconnect(); this.renderer.dispose(); this.renderer.domElement.remove(); this.audioCtx?.close();
  }

  // ------------------------------------------------------------------ speech analysis
  _bands() {
    let data = null;
    if (this.analyser) { this.analyser.getByteFrequencyData(this.freq); data = this.freq; }
    else if (this.freqSource) data = this.freqSource();
    if (!data || !data.length) return null;
    const [lo, hi] = this.freqRange, hz = (hi - lo) / data.length, b = { low: 0, mid: 0, high: 0, air: 0 }, n = { low: 0, mid: 0, high: 0, air: 0 };
    for (let i = 1; i < data.length; i++) {
      const f = lo + i * hz, v = (data[i] / 255) ** 2;
      const k = f < 150 ? null : f < 900 ? "low" : f < 2500 ? "mid" : f < 5000 ? "high" : f < 8000 ? "air" : null;
      if (k) { b[k] += v; n[k]++; }
    }
    for (const k in b) b[k] = Math.sqrt(b[k] / Math.max(1, n[k]));
    b.energy = Math.sqrt(0.5 * b.low ** 2 + 0.35 * b.mid ** 2 + 0.15 * b.high ** 2);
    return b;
  }

  /** Returns {weights, open, pause, emphasis} for this frame from audio. */
  _audioMouth(b, dt) {
    const E = b.energy;
    this.noise = E < this.noise ? approach(this.noise, E, 3, dt) : approach(this.noise, E, 0.08, dt);   // floor tracker
    this.peak = Math.max(E, this.peak * Math.exp(-0.35 * dt));
    this.valley = approach(this.valley, E, E < this.valley ? 30 : 2.5, dt);                 // syllable dips
    this.avgE = approach(this.avgE, E, 1.5, dt);
    const gate = Math.max(0.03, this.noise * 1.8);
    const pause = E < gate * 1.25;
    // mix of syllable contrast (closes between syllables) and absolute level (big vowels open wider)
    const contrast = (E - this.valley) / Math.max(0.08, this.peak - this.valley);
    const level = (E - gate) / Math.max(0.05, this.peak * 0.9 - gate);
    const open = pause ? 0 : clamp(0.65 * clamp(contrast) + 0.35 * clamp(level)) ** 1.15;
    // viseme from the spectrum
    const tot = b.low + b.mid + b.high + b.air + 1e-4;
    const lowR = b.low / tot, highR = (b.high + b.air) / tot, midR = b.mid / tot;
    let v = "A";
    if (open < 0.12) v = this.silentFor < 0.06 ? "MBP" : "rest";
    else if (highR > 0.36 && open < 0.6) v = b.air > b.high * 1.1 ? "S" : "FV";
    else if (lowR > 0.6 && midR < 0.25) v = open > 0.55 ? "O" : "U";
    else if (midR > 0.36 || highR > 0.3) v = "E";
    const emphasis = !pause && E > this.avgE * 1.35 && E > gate * 2.2;
    return { v, open, pause, emphasis };
  }

  // ------------------------------------------------------------------ frame
  _set(name, value) { for (const { mesh, index } of this.morph[name] || []) mesh.morphTargetInfluences[index] = value; }

  _tick() {
    const dt = Math.min(0.05, this.clock.getDelta()), t = this.clock.elapsedTime, now = performance.now();
    if (!this.visible && !this.textTrack && !this.analyser && !this.freqSource) return;
    const S = STATES[this.state];
    const target = { jawOpen: 0, mouthSmile: 0, mouthStretch: 0, mouthFunnel: 0, mouthPucker: 0, mouthRollLower: 0, mouthPress: 0, browInnerUp: 0, browDown: 0 };
    for (const [k, v] of Object.entries(S.face)) target[k] += v;
    if (this.emotion.until < now) this.emotion = { name: "neutral", w: {}, until: Infinity };

    // ---- speech
    let speaking = 0, pause = true, emphasis = false, end = false;
    const b = this._bands();
    if (b && (this.analyser || this.freqSource)) {
      const r = this._audioMouth(b, dt);
      pause = r.pause; emphasis = r.emphasis;
      if (!pause) { this.viseme = r.v; this.visW = r.v === "MBP" ? 0.6 : r.open; speaking = r.open; if (this.state !== "speaking" && r.open > 0.2) this.state = "speaking"; }
      else { this.viseme = "rest"; this.visW = 0; }
      if (pause && this.silentFor > 1.2 && this.state === "speaking") this.state = "listening";
    } else if (this.textTrack) {
      const el = (now - this.textTrack.start) / 1000, tr = this.textTrack.track;
      while (this.textTrack.i < tr.length - 1 && tr[this.textTrack.i + 1].t <= el) {
        this.textTrack.i++; const k = tr[this.textTrack.i];
        if (k.stress) emphasis = true; if (k.end) end = true;
      }
      const k = tr[this.textTrack.i] || { v: "rest", w: 0, pause: true };
      this.viseme = k.v; this.visW = k.w; pause = !!k.pause || k.v === "rest"; speaking = pause ? 0 : k.w;
    } else { this.viseme = "rest"; this.visW = 0; }
    const wasSilent = this.silentFor;
    this.silentFor = pause ? this.silentFor + dt : 0;
    if (!pause && wasSilent > 0.35) this._onPhraseStart();
    if (pause && wasSilent < 0.35 && this.silentFor >= 0.35) this._onPhraseEnd();
    if (end) this._onPhraseEnd();
    if (emphasis && t - this.lastPulse > 0.35) { this.lastPulse = t; this.pulse.brow = 1; this.pulse.nod = 1; }

    // viseme weights (mouth closes fully in pauses)
    const vis = VISEME[this.viseme] || {};
    for (const [k, v] of Object.entries(vis)) target[k] = Math.max(target[k], v * this.visW);
    if (speaking > 0) target.mouthSmile *= 0.6;

    // pulses: eyebrow flash + nod on stressed syllables, smile at phrase ends
    for (const k in this.pulse) this.pulse[k] = approach(this.pulse[k], 0, k === "smile" ? 1.6 : 4.5, dt);
    target.browInnerUp += 0.45 * this.pulse.brow;
    target.mouthSmile += 0.35 * this.pulse.smile;
    // emotions override the resting face
    for (const [k, v] of Object.entries(this.emotion.w)) target[k] = Math.max(target[k], v);
    // idle micro-expressions so the face never freezes
    target.mouthSmile += 0.06 * Math.sin(t * 0.37) * Math.sin(t * 0.11);
    target.browInnerUp += 0.05 * Math.max(0, Math.sin(t * 0.23 + 1));

    for (const [k, v] of Object.entries(target)) {
      const mouth = k.startsWith("mouth") || k === "jawOpen";
      const rate = mouth ? (v > (this.cur[k] ?? 0) ? 30 : 22) : 7;
      this.cur[k] = approach(this.cur[k] ?? 0, clamp(v, 0, k === "mouthPucker" ? 0.6 : 1), rate, dt);
      this._set(k, this.cur[k]);
    }

    // ---- eyes: saccades, glances, pointer, lids follow the gaze
    this._updateGaze(dt, now, speaking);
    const blink = this._updateBlink(dt, S);
    const lidDown = clamp((this.gaze.pitch - 3) / 12) * 0.35;       // looking down lowers the upper lids
    this._set("eyeBlinkLeft", Math.max(blink, lidDown)); this._set("eyeBlinkRight", Math.max(blink, lidDown));
    if (this.eyelids) this.eyelids.visible = Math.max(blink, lidDown) > 0.02;
    for (const e of this.eyes) { e.rotation.set(this.gaze.pitch * DEG, this.gaze.yaw * DEG, 0); }

    // ---- head: state pose + follows the gaze + speech motion + breathing
    const n1 = Math.sin(t * 0.47) * 0.6 + Math.sin(t * 1.13) * 0.4, n2 = Math.sin(t * 0.31 + 1.7) * 0.7 + Math.sin(t * 0.83) * 0.3;
    const talk = speaking * (Math.sin(t * 6.1) * 0.5 + Math.sin(t * 2.7) * 0.5);
    const [hy, hp, hr] = S.head;
    const yaw = hy + this.gaze.yaw * 0.3 + n1 * 1.4 + talk * 1.0;
    const pitch = hp + this.gaze.pitch * 0.2 + n2 * 0.8 + talk * 1.2 + this.pulse.nod * 2.2;
    const roll = hr + n1 * 0.7 + speaking * Math.sin(t * 1.3) * 1.2;
    const mo = this.motion;
    this.head.rotation.x = approach(this.head.rotation.x, pitch * mo * DEG, 5, dt);
    this.head.rotation.y = approach(this.head.rotation.y, yaw * mo * DEG, 4, dt);
    this.head.rotation.z = approach(this.head.rotation.z, roll * mo * DEG, 4, dt);
    this.root.position.y = Math.sin(t * 1.55) * 0.0022 * mo;
    if (this.visible) this.renderer.render(this.scene, this.camera);
  }

  _onPhraseStart() {                     // people often glance away when they start a thought
    if (Math.random() < 0.4) { this.gazeTarget = { yaw: rand(-9, 9), pitch: rand(-6, -2) }; this.glanceUntil = performance.now() + rand(350, 700); }
  }
  _onPhraseEnd() {                       // settle: eye contact, a small smile, often a blink
    this.pulse.smile = 1; this.glanceUntil = 0; this.gazeTarget = { yaw: rand(-1, 1), pitch: rand(-0.5, 0.5) };
    if (Math.random() < 0.6 && this.blinkT < 0) this.nextBlink = 0.05;
  }

  _updateGaze(dt, now, speaking) {
    this.nextSaccade -= dt;
    if (now > this.glanceUntil && this.nextSaccade <= 0) {
      const p = this.pointer && now - this.pointer.t < 4000 ? this.pointer : null;
      let yaw, pitch, wait;
      if (this.state === "thinking") { yaw = rand(-12, -6); pitch = rand(-8, -4); wait = rand(0.8, 1.8); }
      else if (this.state === "listening") { yaw = rand(-1.5, 1.5); pitch = rand(-1, 1); wait = rand(0.5, 1.4); }   // eye contact + micro-saccades
      else if (this.state === "speaking") { const away = Math.random() < 0.15; yaw = away ? rand(-8, 8) : rand(-2, 2); pitch = away ? rand(-4, 2) : rand(-1, 1); wait = rand(0.6, 1.6); }
      else { const wander = Math.random() < 0.45; yaw = wander ? rand(-10, 10) : rand(-2, 2); pitch = wander ? rand(-5, 4) : rand(-1, 1); wait = rand(1.0, 3.2); }
      if (p && this.state !== "thinking") { yaw = yaw * 0.3 + p.x * 12; pitch = pitch * 0.3 - p.y * 7; }
      const jump = Math.hypot(yaw - this.gazeTarget.yaw, pitch - this.gazeTarget.pitch);
      this.gazeTarget = { yaw, pitch }; this.nextSaccade = wait;
      if (jump > 9 && Math.random() < 0.35 && this.blinkT < 0) this.nextBlink = 0.02;   // blink with big eye shifts
    }
    // saccades are fast but not instant
    this.gaze.yaw = approach(this.gaze.yaw, this.gazeTarget.yaw, 22, dt);
    this.gaze.pitch = approach(this.gaze.pitch, this.gazeTarget.pitch, 22, dt);
  }

  _updateBlink(dt, S) {
    this.nextBlink -= dt;
    if (this.blinkT < 0 && this.nextBlink <= 0) { this.blinkT = 0; this.doubleBlink = Math.random() < 0.15; }
    if (this.blinkT < 0) return 0;
    this.blinkT += dt;
    const close = 0.07, hold = 0.03, open = 0.11, T = close + hold + open, x = this.blinkT;
    const v = x < close ? x / close : x < close + hold ? 1 : Math.max(0, 1 - (x - close - hold) / open);
    if (x >= T) {
      if (this.doubleBlink) { this.doubleBlink = false; this.blinkT = -1; this.nextBlink = 0.09; }
      else { this.blinkT = -1; const [lo, hi] = S.blink; this.nextBlink = rand(lo, hi); }
    }
    return v;
  }
}
export { MaryamAvatar as AylaAvatar };

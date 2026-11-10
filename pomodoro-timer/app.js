"use strict";

const DURATIONS = {
  work: 25 * 60,
  short: 5 * 60,
  long: 15 * 60,
};

const LABELS = {
  work: "Work",
  short: "Short break",
  long: "Long break",
};

const RING_RADIUS = 90;
const RING_LENGTH = 2 * Math.PI * RING_RADIUS;

const params = new URLSearchParams(window.location.search);
const preview = params.get("demo") === "1";

if (preview) {
  DURATIONS.work = 8;
  DURATIONS.short = 4;
  DURATIONS.long = 6;
}

const phaseEl = document.querySelector("#phase");
const timeEl = document.querySelector("#time");
const progressEl = document.querySelector("#progress");
const statusEl = document.querySelector("#status");
const cycleEl = document.querySelector("#cycle");
const previewEl = document.querySelector("#preview");
const dots = Array.from(document.querySelectorAll("#dots span"));
const modeButtons = Array.from(document.querySelectorAll(".modes button"));
const startBtn = document.querySelector("#start");
const pauseBtn = document.querySelector("#pause");
const resetBtn = document.querySelector("#reset");

let mode = "work";
let remainingMs = DURATIONS.work * 1000;
let completedWork = 0;
let running = false;
let cue = false;
let endAt = 0;
let tickId = 0;
let endId = 0;
let finishing = false;
let audioCtx = null;

function formatMs(ms) {
  const totalSeconds = ms <= 0 ? 0 : Math.ceil(ms / 1000 - 1e-9);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function spokenTime(ms) {
  const totalSeconds = ms <= 0 ? 0 : Math.ceil(ms / 1000 - 1e-9);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  const minuteLabel = minutes === 1 ? "1 minute" : `${minutes} minutes`;
  const secondLabel = seconds === 1 ? "1 second" : `${seconds} seconds`;
  return `${minuteLabel}, ${secondLabel}`;
}

function roundProgress() {
  const earnedLongBreak = mode === "long" && completedWork > 0 && completedWork % 4 === 0;
  const doneInRound = earnedLongBreak ? 4 : completedWork % 4;
  const round = earnedLongBreak ? completedWork / 4 : Math.floor(completedWork / 4) + 1;
  return { doneInRound, round };
}

function clearTimers() {
  window.clearInterval(tickId);
  window.clearTimeout(endId);
  tickId = 0;
  endId = 0;
}

function setStatus(text, isCue) {
  cue = isCue;
  statusEl.textContent = text;
  statusEl.classList.toggle("cue", isCue);
  document.body.classList.toggle("is-cue", isCue);
}

function ensureAudio() {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return null;
    if (!audioCtx) audioCtx = new AudioContext();
    if (audioCtx.state === "suspended") audioCtx.resume();
    return audioCtx;
  } catch (error) {
    return null;
  }
}

function chime(finishedMode) {
  const ctx = audioCtx;
  if (!ctx) return;
  const notes = finishedMode === "work" ? [523.25, 659.25, 783.99] : [783.99, 523.25];
  const start = ctx.currentTime + 0.02;
  notes.forEach((freq, index) => {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    const at = start + index * 0.18;
    osc.type = "sine";
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(0.0001, at);
    gain.gain.exponentialRampToValueAtTime(0.12, at + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, at + 0.38);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(at);
    osc.stop(at + 0.4);
    osc.onended = () => {
      osc.disconnect();
      gain.disconnect();
    };
  });
}

function cueCopy(finishedMode) {
  if (finishedMode === "work" && mode === "long") {
    return "Four work sessions done. Take a long break.";
  }
  if (finishedMode === "work") {
    return "Work session finished. Short break is ready.";
  }
  if (finishedMode === "long") {
    return "Long break finished. A new round is ready.";
  }
  return "Break finished. The next work session is ready.";
}

function finishSession() {
  if (finishing || !running) return;
  finishing = true;
  running = false;
  clearTimers();

  const finishedMode = mode;
  if (finishedMode === "work") {
    completedWork += 1;
    // A long break follows every 4th work session that actually reaches zero.
    mode = completedWork % 4 === 0 ? "long" : "short";
  } else {
    mode = "work";
  }

  remainingMs = DURATIONS[mode] * 1000;
  setStatus(cueCopy(finishedMode), true);
  try {
    chime(finishedMode);
  } catch (error) {
    // The highlighted message is the cue when audio is unavailable.
  }
  render();
  finishing = false;
}

function onTick() {
  if (!running) return;
  const left = endAt - Date.now();
  if (left <= 0) {
    finishSession();
    return;
  }
  remainingMs = left;
  render();
}

function start() {
  if (running) return;
  ensureAudio();
  if (remainingMs <= 0) remainingMs = DURATIONS[mode] * 1000;
  running = true;
  endAt = Date.now() + remainingMs;
  clearTimers();
  tickId = window.setInterval(onTick, 100);
  endId = window.setTimeout(finishSession, remainingMs);
  setStatus(`${LABELS[mode]} started.`, false);
  render();
}

function pause() {
  if (!running) return;
  const left = endAt - Date.now();
  if (left <= 0) {
    finishSession();
    return;
  }
  remainingMs = left;
  running = false;
  clearTimers();
  setStatus("Paused.", false);
  render();
}

function reset() {
  running = false;
  clearTimers();
  remainingMs = DURATIONS[mode] * 1000;
  setStatus("Timer reset.", false);
  render();
}

function selectMode(next) {
  if (!Object.prototype.hasOwnProperty.call(DURATIONS, next)) return;
  if (next === mode) return;

  running = false;
  clearTimers();
  mode = next;
  remainingMs = DURATIONS[mode] * 1000;
  setStatus(`${LABELS[mode]} selected.`, false);
  render();
}

function render() {
  const totalMs = DURATIONS[mode] * 1000;
  const fraction = Math.min(1, Math.max(0, remainingMs / totalMs));
  const label = LABELS[mode];
  const clock = formatMs(remainingMs);
  const { doneInRound, round } = roundProgress();

  document.body.dataset.mode = mode;
  phaseEl.textContent = label;
  timeEl.textContent = clock;
  timeEl.setAttribute("aria-label", `${spokenTime(remainingMs)} remaining, ${label}`);
  progressEl.style.strokeDasharray = String(RING_LENGTH);
  progressEl.style.strokeDashoffset = String(RING_LENGTH * (1 - fraction));

  modeButtons.forEach((button) => {
    button.setAttribute("aria-checked", button.dataset.mode === mode ? "true" : "false");
  });

  startBtn.disabled = running;
  pauseBtn.disabled = !running;
  startBtn.classList.toggle("primary", !running);
  startBtn.classList.toggle("ghost", running);
  pauseBtn.classList.toggle("primary", running);
  pauseBtn.classList.toggle("ghost", !running);

  dots.forEach((dot, index) => {
    dot.classList.toggle("is-done", index < doneInRound);
  });

  const sessionWord = doneInRound === 1 ? "work session" : "work sessions";
  cycleEl.textContent = `Round ${round} · ${doneInRound} of 4 ${sessionWord}`;

  document.title = cue ? `${label} ready — Pomodoro` : `${clock} · ${label} — Pomodoro`;
}

startBtn.addEventListener("click", start);
pauseBtn.addEventListener("click", pause);
resetBtn.addEventListener("click", reset);

modeButtons.forEach((button) => {
  button.addEventListener("click", () => selectMode(button.dataset.mode));
});

document.querySelector(".modes").addEventListener("keydown", (event) => {
  const buttons = modeButtons;
  const index = buttons.indexOf(document.activeElement);
  if (index < 0) return;
  let next = index;
  if (event.key === "ArrowRight" || event.key === "ArrowDown") {
    next = (index + 1) % buttons.length;
  } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
    next = (index - 1 + buttons.length) % buttons.length;
  } else {
    return;
  }
  event.preventDefault();
  buttons[next].focus();
  selectMode(buttons[next].dataset.mode);
});

document.addEventListener("keydown", (event) => {
  if (event.repeat || event.metaKey || event.ctrlKey || event.altKey) return;
  const target = event.target instanceof Element ? event.target : null;
  const onButton = Boolean(target && target.closest("button"));

  if (event.code === "Space") {
    if (onButton) return;
    event.preventDefault();
    if (running) pause();
    else start();
  } else if (event.key === "r" || event.key === "R") {
    event.preventDefault();
    reset();
  }
});

document.addEventListener("visibilitychange", onTick);
window.addEventListener("focus", onTick);

if (preview) {
  previewEl.hidden = false;
  previewEl.textContent = `Preview timings: ${DURATIONS.work}s work, ${DURATIONS.short}s short break, ${DURATIONS.long}s long break.`;
  setStatus("Press Start. Preview timings are shortened.", false);
}

render();

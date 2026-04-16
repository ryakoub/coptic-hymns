const audio = document.getElementById("audio");
const lyricsContainer = document.getElementById("lyrics");

const params = new URLSearchParams(window.location.search);
const hymn = params.get("hymn");
const group = params.get("group") || "grades-3-4";
const level = params.get("level") || "level-1";
const syncDebugEnabled = params.get("syncDebug") === "1";
const seekDebounceMs = Number(params.get("seekDebounceMs") || 0);
const rawSyncOffset = params.get("syncOffsetMs");
const ua = navigator.userAgent || "";
const isIOS = /iPhone|iPad|iPod/i.test(ua);
const isSafari = /Safari/i.test(ua) && !/Chrome|CriOS|Edg|OPR|FxiOS/i.test(ua);
const browserOffsetMs = 0;
const syncOffsetMs = rawSyncOffset !== null ? Number(rawSyncOffset) : browserOffsetMs;
const syncOffsetSec = syncOffsetMs / 1000;
const syncDebugBuild = "20260413j";

async function pickPreferredAudioUrl(primaryUrl) {
if (typeof primaryUrl !== "string" || !primaryUrl.includes("audio.mp3")) {
return primaryUrl;
}

const seekUrl = primaryUrl.replace("audio.mp3", "audio.seek.m4a");
try {
const res = await fetch(seekUrl, { method: "HEAD" });
if (res.ok) {
return seekUrl;
}
} catch (_) {
// Fallback to original URL when the seek-friendly file is missing.
}

return primaryUrl;
}

// Fix Hymn List nav link to return to the correct group/level
document.getElementById("hymnListLink").href = `hymns.html?group=${group}&level=${level}`;

// Show group and level subtitle
const groupLabel = group === "college" 
  ? "COLLEGE & UP" 
  : group.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase());
const levelLabel = level.replace("level-", "Level ");
document.getElementById("subtitle").textContent = `${groupLabel} · ${levelLabel}`;
document.title = `${groupLabel} ${levelLabel} | Coptic Chanter`;

const toggleLoopBtn = document.getElementById("toggleLoop");
const toggleScrollBtn = document.getElementById("toggleScroll");
const toggleCopticFontBtn = document.getElementById("toggleCopticFont");
const toggleSettingsBtn = document.getElementById("toggleSettings");
const settingsPanel = document.getElementById("settingsPanel");
const toggleAdvancedBtn = document.getElementById("toggleAdvanced");
const advancedPanel = document.getElementById("advancedPanel");
const timestampsBox = document.getElementById("timestamps");
const audioNav = document.querySelector(".audio-nav");
const audioSpacer = document.querySelector(".audio-spacer");

let repeatVerseEnabled = false;
let autoScrollEnabled = true;
let currentLineIndex = -1;
let currentLines = [];
let capturedTimes = [];
let loopTargetIndex = null;
let currentWordKey = null;
let currentStanzaKey = null;
let latestSeekToken = 0;
let isSeekInFlight = false;
let pendingSeek = null;
let syncRafId = null;
let syncDebugPanel = null;
let seekRequestCount = 0;

function ensureSyncDebugPanel() {
if (!syncDebugEnabled || syncDebugPanel) return;
syncDebugPanel = document.createElement("div");
syncDebugPanel.id = "syncDebugPanel";
syncDebugPanel.style.cssText = [
"position:fixed",
"right:10px",
"bottom:10px",
"z-index:9999",
"max-width:84vw",
"padding:8px 10px",
"border-radius:8px",
"background:rgba(7,22,37,0.88)",
"color:#cfe8ff",
"font:12px/1.35 monospace",
"white-space:pre-wrap",
"pointer-events:none"
].join(";");
document.body.appendChild(syncDebugPanel);
}

function setSyncDebug(text) {
if (!syncDebugEnabled) return;
ensureSyncDebugPanel();
if (syncDebugPanel) {
syncDebugPanel.textContent = `build=${syncDebugBuild}\ntaps=${seekRequestCount}\nbrowser=${isSafari ? "safari" : "other"}${isIOS ? "-ios" : ""}\nautoOffset=${browserOffsetMs}ms\noffset=${syncOffsetMs}ms\n${text}`;
}
}

function clearActiveLyricsState() {
currentLines.forEach(line => {
line.element?.classList.remove("active");
if (Array.isArray(line.words)) {
line.words.forEach(word => word.element?.classList.remove("active-word"));
}
if (Array.isArray(line.stanzas)) {
line.stanzas.forEach(s => s.element?.classList.remove("active-stanza"));
}
});
currentLineIndex = -1;
currentWordKey = null;
currentStanzaKey = null;
}

function syncLyricsToTime(t, lines) {
const effectiveTime = Math.max(0, t - syncOffsetSec);
let activeIndex = -1;
for (let i = 0; i < lines.length; i++) {
const l = lines[i];
const next = lines[i + 1];
if (effectiveTime >= l.start && (!next || effectiveTime < next.start)) {
activeIndex = i;
break;
}
}

if (activeIndex !== -1 && activeIndex !== currentLineIndex) {
currentLines.forEach(x => x.element.classList.remove("active"));
currentLines[activeIndex].element.classList.add("active");
currentLineIndex = activeIndex;

if (autoScrollEnabled) {
const el = currentLines[activeIndex].element;
const elRect = el.getBoundingClientRect();
const audioBarTop = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--audio-bar-top")) || 0;
const audioBarHeight = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--audio-bar-height")) || 0;
const clearanceTop = audioBarTop + audioBarHeight + 12; // px below the fixed audio bar
const elIsAboveBar = elRect.top < clearanceTop;
const elIsBelowViewport = elRect.top > window.innerHeight * 0.75;
if (elIsAboveBar || elIsBelowViewport) {
const targetScrollY = window.scrollY + elRect.top - clearanceTop;
window.scrollTo({ top: targetScrollY, behavior: "smooth" });
}
}
}

if (activeIndex === -1 && currentLineIndex !== -1) {
currentLines.forEach(x => x.element.classList.remove("active"));
currentLineIndex = -1;
}

let activeWordKey = null;
if (activeIndex !== -1) {
const activeLine = currentLines[activeIndex];
if (Array.isArray(activeLine.words) && activeLine.words.length) {
for (let i = 0; i < activeLine.words.length; i++) {
const word = activeLine.words[i];
const wordEnd = Number.isFinite(word.end)
? word.end
: activeLine.words[i + 1]?.start ?? currentLines[activeIndex + 1]?.start ?? audio.duration;
if (effectiveTime >= word.start && (!Number.isFinite(wordEnd) || effectiveTime < wordEnd)) {
activeWordKey = `${activeIndex}-${i}`;
break;
}
}
}
}

if (activeWordKey !== currentWordKey) {
currentLines.forEach(line => {
if (Array.isArray(line.words)) {
line.words.forEach(word => word.element?.classList.remove("active-word"));
}
});

if (activeWordKey) {
const [lineIndex, wordIndex] = activeWordKey.split("-").map(Number);
currentLines[lineIndex]?.words?.[wordIndex]?.element?.classList.add("active-word");
}

currentWordKey = activeWordKey;
}

// stanza-level highlight
let activeStanzaKey = null;
if (activeIndex !== -1) {
const activeLine = currentLines[activeIndex];
if (Array.isArray(activeLine.stanzas) && activeLine.stanzas.length) {
for (let i = 0; i < activeLine.stanzas.length; i++) {
const s = activeLine.stanzas[i];
const sEnd = activeLine.stanzas[i + 1]?.start ?? currentLines[activeIndex + 1]?.start ?? audio.duration;
if (effectiveTime >= s.start && (!Number.isFinite(sEnd) || effectiveTime < sEnd)) {
activeStanzaKey = `${activeIndex}-s${i}`;
break;
}
}
}
}

if (activeStanzaKey !== currentStanzaKey) {
currentLines.forEach(line => {
if (Array.isArray(line.stanzas)) {
line.stanzas.forEach(s => s.element?.classList.remove("active-stanza"));
}
});

if (activeStanzaKey) {
const [lineIndex, stanzaIdx] = activeStanzaKey.split("-s").map(Number);
currentLines[lineIndex]?.stanzas?.[stanzaIdx]?.element?.classList.add("active-stanza");
}

currentStanzaKey = activeStanzaKey;
}
}

function seekToTime(time, lineIndex) {
if (!Number.isFinite(time)) return;
seekRequestCount += 1;
pendingSeek = { time, lineIndex, queuedAt: performance.now() };
setSyncDebug(
`tap #${seekRequestCount}\ntarget=${time.toFixed(2)}s\nqueue=${isSeekInFlight ? "replace-pending" : "start-now"}\ndebounce=${seekDebounceMs}ms`
);
processSeekQueue();
}

async function waitForSeekLanding(targetTime, seekToken) {
await new Promise(resolve => {
let settled = false;
const SEEK_TOLERANCE = 0.08;
const seekStartedAt = performance.now();
let timeoutId = null;
const hasLanded = () => Math.abs(audio.currentTime - targetTime) <= SEEK_TOLERANCE;
const settle = () => {
if (settled) return;
settled = true;
audio.removeEventListener("seeked", onSeeked);
audio.removeEventListener("timeupdate", onTimeUpdate);
clearTimeout(timeoutId);
const landed = audio.currentTime;
const drift = landed - targetTime;
setSyncDebug(
`seek landed\ntarget=${targetTime.toFixed(2)}s\nlanded=${landed.toFixed(2)}s\ndrift=${drift.toFixed(3)}s\nsettle=${(performance.now() - seekStartedAt).toFixed(0)}ms\ntoken=${seekToken}`
);
resolve();
};
const onSeeked = () => {
if (hasLanded()) {
settle();
}
};
const onTimeUpdate = () => {
if (hasLanded()) {
settle();
}
};

audio.addEventListener("seeked", onSeeked);
audio.addEventListener("timeupdate", onTimeUpdate);
audio.currentTime = targetTime;

if (hasLanded()) {
settle();
return;
}

timeoutId = setTimeout(() => {
audio.currentTime = targetTime;
settle();
}, 1200);
});
}

async function processSeekQueue() {
if (isSeekInFlight) return;
isSeekInFlight = true;

while (pendingSeek) {
const { time, lineIndex } = pendingSeek;
pendingSeek = null;

const seekToken = ++latestSeekToken;
setSyncDebug(`seek start\ntarget=${time.toFixed(2)}s\ntoken=${seekToken}`);

if (repeatVerseEnabled) {
loopTargetIndex = lineIndex;
}

clearActiveLyricsState();
audio.pause();
await waitForSeekLanding(time, seekToken);

// If a newer request arrived while waiting, skip this resume.
if (seekToken !== latestSeekToken || pendingSeek) {
continue;
}

const playPromise = audio.play();
if (playPromise && typeof playPromise.then === "function") {
try {
await playPromise;
} catch (_) {
setSyncDebug(`play blocked\ntarget=${time.toFixed(2)}s\ntoken=${seekToken}`);
continue;
}
}

if (seekToken !== latestSeekToken || pendingSeek) {
continue;
}

syncLyricsToTime(audio.currentTime, currentLines);
setSyncDebug(
`playing\ntarget=${time.toFixed(2)}s\ncurrent=${audio.currentTime.toFixed(2)}s\neffective=${Math.max(0, audio.currentTime - syncOffsetSec).toFixed(2)}s\ndelta=${(audio.currentTime - time).toFixed(3)}s\noffset=${syncOffsetMs}ms`
);
}

isSeekInFlight = false;
}

function syncFrame() {
if (!audio.paused && !audio.ended && !isSeekInFlight) {
const t = audio.currentTime;

if (repeatVerseEnabled && loopTargetIndex !== null && currentLines[loopTargetIndex]) {
const loopLine = currentLines[loopTargetIndex];
const loopNext = currentLines[loopTargetIndex + 1];
const loopEnd = loopNext ? loopNext.start : audio.duration;
if (Number.isFinite(loopEnd) && t >= loopEnd - 0.03) {
audio.currentTime = loopLine.start;
audio.play();
syncRafId = requestAnimationFrame(syncFrame);
return;
}
}

syncLyricsToTime(t, currentLines);
}

syncRafId = requestAnimationFrame(syncFrame);
}

function startSyncLoop() {
if (syncRafId !== null) return;
syncRafId = requestAnimationFrame(syncFrame);
}

function stopSyncLoop() {
  if (syncRafId !== null) {
    cancelAnimationFrame(syncRafId);
    syncRafId = null;
  }
  // Don't clear highlights if pause was fired by seek machinery
  if (!isSeekInFlight) {
    clearActiveLyricsState();
  }
}

const COPTIC_FONT_PREF_KEY = "copticFontMode";

function applyCopticFontMode(mode) {
const useTraditional = mode === "traditional";
document.body.classList.toggle("coptic-font-traditional", useTraditional);
if (toggleCopticFontBtn) {
toggleCopticFontBtn.textContent = `Coptic Font: ${useTraditional ? "Traditional" : "Modern"}`;
}
}

const savedCopticMode = localStorage.getItem(COPTIC_FONT_PREF_KEY) || "traditional";
applyCopticFontMode(savedCopticMode);

const base = `content/mahragan-keraza-2026/${group}/${level}/${hymn}`;

function updateAudioBarOffset() {
const nav = document.querySelector("nav.nav-bar");
if (!nav || !audioNav) return;
const navRect = nav.getBoundingClientRect();
const top = Math.ceil(navRect.bottom + 10);
const audioHeight = Math.ceil(audioNav.getBoundingClientRect().height || 0);
document.documentElement.style.setProperty("--audio-bar-top", `${top}px`);
document.documentElement.style.setProperty("--audio-bar-height", `${audioHeight}px`);
if (audioSpacer) {
audioSpacer.style.height = `${audioHeight + 16}px`;
}
}

updateAudioBarOffset();
window.addEventListener("resize", updateAudioBarOffset);
window.addEventListener("load", updateAudioBarOffset);
window.addEventListener("pageshow", updateAudioBarOffset);
window.visualViewport?.addEventListener("resize", updateAudioBarOffset);
window.visualViewport?.addEventListener("scroll", updateAudioBarOffset);

if (typeof ResizeObserver !== "undefined") {
const nav = document.querySelector("nav.nav-bar");
if (nav) {
new ResizeObserver(updateAudioBarOffset).observe(nav);
}
new ResizeObserver(updateAudioBarOffset).observe(audioNav);
}

audio.src = `${base}/audio.mp3`;

fetch(`${base}/info.json`)
.then(r=>r.json())
.then(async info=>{
document.getElementById("title").innerText = info.title;
document.title = `${info.title} | Coptic Chanter`;
document.getElementById("youtubeLink").href = info.youtube;
const source = info.audio || `${base}/audio.mp3`;
audio.src = await pickPreferredAudioUrl(source);
setSyncDebug(`audio\nsource=${audio.src.split("/").pop()}`);

const antiphonalGroup = info.antiphonalGroup || 1;

fetch(`${base}/lyrics.json`)
.then(r=>r.json())
.then(lines=>{
currentLines = lines;

lines.forEach((line, index)=>{

const div=document.createElement("div");
div.className="line";
div.classList.add(`color-group-${Math.floor(index / antiphonalGroup) % 2}`);

const copticDiv = document.createElement("div");
copticDiv.className = "coptic";

if (Array.isArray(line.words) && line.words.length) {
line.words.forEach((word, wordIndex) => {
const wordSpan = document.createElement("span");
wordSpan.className = "word";
wordSpan.textContent = word.text || "";
wordSpan.dataset.wordKey = `${index}-${wordIndex}`;
wordSpan.style.cursor = "pointer";
wordSpan.addEventListener("click", (event) => {
event.stopPropagation();
if (Number.isFinite(word.start)) {
seekToTime(word.start, index);
}
});
copticDiv.appendChild(wordSpan);
if (word.trailingSpace !== false) {
copticDiv.appendChild(document.createTextNode(" "));
}
word.element = wordSpan;
});
} else if (Array.isArray(line.stanzas) && line.stanzas.length) {
line.stanzas.forEach((stanza, si) => {
const span = document.createElement("span");
span.className = "stanza";
span.textContent = stanza.coptic;
span.style.cursor = "pointer";
span.addEventListener("click", (event) => {
event.stopPropagation();
if (Number.isFinite(stanza.start)) {
seekToTime(stanza.start, index);
}
});
copticDiv.appendChild(span);
if (si < line.stanzas.length - 1) {
copticDiv.appendChild(document.createTextNode(" "));
}
stanza.element = span;
});
} else {
copticDiv.textContent = line.coptic;
}

const translationDiv = document.createElement("div");
translationDiv.className = "translation";
translationDiv.textContent = line.translations?.english || "";

div.appendChild(copticDiv);
div.appendChild(translationDiv);

div.onclick=()=>{
seekToTime(line.start, index);
};

lyricsContainer.appendChild(div);
line.element=div;

});

audio.ontimeupdate=()=>{
if (audio.paused || isSeekInFlight) {
return;
}
syncLyricsToTime(audio.currentTime, lines);

};

audio.addEventListener("seeked", () => {
syncLyricsToTime(audio.currentTime, lines);
});

audio.addEventListener("play", startSyncLoop);
audio.addEventListener("playing", startSyncLoop);
audio.addEventListener("pause", stopSyncLoop);
audio.addEventListener("ended", stopSyncLoop);

});

}); // end info.json fetch

toggleLoopBtn?.addEventListener("click", () => {
repeatVerseEnabled = !repeatVerseEnabled;
if (repeatVerseEnabled) {
loopTargetIndex = currentLineIndex >= 0 ? currentLineIndex : 0;
} else {
loopTargetIndex = null;
}
toggleLoopBtn.textContent = `Repeat Verse: ${repeatVerseEnabled ? "On" : "Off"}`;
});

toggleScrollBtn?.addEventListener("click", () => {
autoScrollEnabled = !autoScrollEnabled;
toggleScrollBtn.textContent = `Auto-Scroll: ${autoScrollEnabled ? "On" : "Off"}`;
});

toggleCopticFontBtn?.addEventListener("click", () => {
const currentMode = document.body.classList.contains("coptic-font-traditional") ? "traditional" : "modern";
const nextMode = currentMode === "traditional" ? "modern" : "traditional";
applyCopticFontMode(nextMode);
localStorage.setItem(COPTIC_FONT_PREF_KEY, nextMode);
});

toggleSettingsBtn?.addEventListener("click", () => {
if (!settingsPanel) return;
const isHidden = settingsPanel.hasAttribute("hidden");
if (isHidden) {
settingsPanel.removeAttribute("hidden");
toggleSettingsBtn.setAttribute("aria-expanded", "true");
toggleSettingsBtn.textContent = "✕";
toggleSettingsBtn.setAttribute("aria-label", "Close settings");
toggleSettingsBtn.title = "Close settings";
} else {
settingsPanel.setAttribute("hidden", "");
toggleSettingsBtn.setAttribute("aria-expanded", "false");
toggleSettingsBtn.textContent = "⚙";
toggleSettingsBtn.setAttribute("aria-label", "Open settings");
toggleSettingsBtn.title = "Settings";
advancedPanel?.setAttribute("hidden", "");
toggleAdvancedBtn?.setAttribute("aria-expanded", "false");
if (toggleAdvancedBtn) {
toggleAdvancedBtn.textContent = "Advanced Options";
}
}
});

document.addEventListener("click", (event) => {
if (!toggleSettingsBtn || !settingsPanel || settingsPanel.hasAttribute("hidden")) {
return;
}

const target = event.target;
if (target instanceof Node && !settingsPanel.contains(target) && !toggleSettingsBtn.contains(target)) {
settingsPanel.setAttribute("hidden", "");
toggleSettingsBtn?.setAttribute("aria-expanded", "false");
if (toggleSettingsBtn) {
toggleSettingsBtn.textContent = "⚙";
toggleSettingsBtn.setAttribute("aria-label", "Open settings");
toggleSettingsBtn.title = "Settings";
}
advancedPanel?.setAttribute("hidden", "");
toggleAdvancedBtn?.setAttribute("aria-expanded", "false");
if (toggleAdvancedBtn) {
toggleAdvancedBtn.textContent = "Advanced Options";
}
}
});

toggleAdvancedBtn?.addEventListener("click", () => {
if (!advancedPanel) return;
const isHidden = advancedPanel.hasAttribute("hidden");
if (isHidden) {
advancedPanel.removeAttribute("hidden");
toggleAdvancedBtn.setAttribute("aria-expanded", "true");
toggleAdvancedBtn.textContent = "Advanced Options: On";
} else {
advancedPanel.setAttribute("hidden", "");
toggleAdvancedBtn.setAttribute("aria-expanded", "false");
toggleAdvancedBtn.textContent = "Advanced Options";
}
});

// Timestamp capture tool: Press "T" to log current time
document.addEventListener("keydown", function(e){
    if(e.key === "t" || e.key === "T"){
        const time = audio.currentTime.toFixed(2);
        capturedTimes.push(time);
        console.log(`Timestamp: ${time}`);
        if (timestampsBox) {
            timestampsBox.textContent = `Timestamps (${capturedTimes.length})\n${capturedTimes.join("\n")}`;
        }
    }
});
const audio = document.getElementById("audio");
const lyricsContainer = document.getElementById("lyrics");

const params = new URLSearchParams(window.location.search);
const hymn = params.get("hymn");
const group = params.get("group") || "grades-3-4";
const level = params.get("level") || "level-1";

// Fix Hymn List nav link to return to the correct group/level
document.getElementById("hymnListLink").href = `hymns.html?group=${group}&level=${level}`;

// Show group and level subtitle
const groupLabel = group.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase());
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
let queuedSeekTime = null;
let seekFlushScheduled = false;
let suppressLoopUntil = 0;
let seekRequestId = 0;
let pendingSeek = null;
let seekCompletionTimer = null;

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

function setActiveLine(index) {
if (currentLineIndex === index) {
return;
}

currentLines.forEach(line => line.element?.classList.remove("active"));

if (index >= 0) {
currentLines[index]?.element?.classList.add("active");
}

currentLineIndex = index;
}

function setActiveWord(wordKey) {
if (currentWordKey === wordKey) {
return;
}

currentLines.forEach(line => {
if (Array.isArray(line.words)) {
line.words.forEach(word => word.element?.classList.remove("active-word"));
}
});

if (wordKey) {
const [lineIndex, wordIndex] = wordKey.split("-").map(Number);
currentLines[lineIndex]?.words?.[wordIndex]?.element?.classList.add("active-word");
}

currentWordKey = wordKey;
}

function flushQueuedSeek() {
if (!Number.isFinite(queuedSeekTime)) {
return;
}

const targetTime = queuedSeekTime;
const requestId = seekRequestId;
queuedSeekTime = null;

const finishSeek = () => {
if (requestId !== seekRequestId) {
return;
}
if (seekCompletionTimer) {
window.clearTimeout(seekCompletionTimer);
seekCompletionTimer = null;
}
audio.play().catch(() => {});
};

const performSeek = () => {
if (requestId !== seekRequestId) {
return;
}

audio.pause();

if (Math.abs(audio.currentTime - targetTime) < 0.01) {
finishSeek();
return;
}

const confirmSeek = () => {
if (requestId !== seekRequestId) {
return;
}

if (Math.abs(audio.currentTime - targetTime) <= 0.5) {
finishSeek();
}
};

audio.addEventListener("seeked", confirmSeek, { once: true });

audio.currentTime = targetTime;

if (seekCompletionTimer) {
window.clearTimeout(seekCompletionTimer);
}
seekCompletionTimer = window.setTimeout(() => {
confirmSeek();
}, 250);
};

if (audio.readyState >= 1 && Number.isFinite(audio.duration)) {
performSeek();
return;
}

pendingSeek = { requestId, targetTime };
audio.load();
}

function seekTo(time, options = {}) {
const targetTime = Number(time);
if (!Number.isFinite(targetTime)) {
return;
}

seekRequestId += 1;
queuedSeekTime = targetTime;
const cooldownMs = Number.isFinite(options.suppressLoopMs) ? options.suppressLoopMs : 250;
suppressLoopUntil = performance.now() + cooldownMs;

if (Number.isInteger(options.lineIndex)) {
setActiveLine(options.lineIndex);
if (repeatVerseEnabled) {
loopTargetIndex = options.lineIndex;
}
}

setActiveWord(options.wordKey || null);

if (seekFlushScheduled) {
return;
}

seekFlushScheduled = true;
requestAnimationFrame(() => {
seekFlushScheduled = false;
flushQueuedSeek();
});
}

audio.src = `${base}/audio.mp3`;
audio.preload = "auto";

fetch(`${base}/info.json`)
.then(r=>r.json())
.then(info=>{
document.getElementById("title").innerText = info.title;
document.title = `${info.title} | Coptic Chanter`;
document.getElementById("youtubeLink").href = info.youtube;
if (info.audio && info.audio !== audio.currentSrc && info.audio !== audio.getAttribute("src")) {
audio.src = info.audio;
}
});

function retryPendingSeek() {
if (!pendingSeek) {
return;
}

const { requestId, targetTime } = pendingSeek;

if (requestId !== seekRequestId) {
pendingSeek = null;
return;
}

if (audio.readyState < 1 || !Number.isFinite(audio.duration)) {
return;
}

pendingSeek = null;
queuedSeekTime = targetTime;
flushQueuedSeek();
}

audio.addEventListener("loadedmetadata", retryPendingSeek);
audio.addEventListener("loadeddata", retryPendingSeek);
audio.addEventListener("canplay", retryPendingSeek);

fetch(`${base}/lyrics.json`)
.then(r=>r.json())
.then(lines=>{
currentLines = lines;

lines.forEach((line, index)=>{

const div=document.createElement("div");
div.className="line";

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
seekTo(word.start, { lineIndex: index, wordKey: wordSpan.dataset.wordKey });
}
});
copticDiv.appendChild(wordSpan);
if (word.trailingSpace !== false) {
copticDiv.appendChild(document.createTextNode(" "));
}
word.element = wordSpan;
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
seekTo(line.start, { lineIndex: index });
};

lyricsContainer.appendChild(div);
line.element=div;

});

audio.ontimeupdate=()=>{
const t=audio.currentTime;

if (
repeatVerseEnabled &&
loopTargetIndex !== null &&
currentLines[loopTargetIndex] &&
!audio.seeking &&
performance.now() >= suppressLoopUntil
) {
const loopLine = currentLines[loopTargetIndex];
const loopNext = currentLines[loopTargetIndex + 1];
const loopEnd = loopNext ? loopNext.start : audio.duration;
if (Number.isFinite(loopEnd) && t >= loopEnd - 0.03) {
seekTo(loopLine.start, { suppressLoopMs: 300 });
return;
}
}

let activeIndex = -1;
for (let i = 0; i < lines.length; i++) {
const l = lines[i];
const next = lines[i + 1];
if (t >= l.start && (!next || t < next.start)) {
activeIndex = i;
break;
}
}

if (activeIndex !== -1 && activeIndex !== currentLineIndex) {
setActiveLine(activeIndex);

if (autoScrollEnabled) {
currentLines[activeIndex].element.scrollIntoView({ behavior: "smooth", block: "center" });
}
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
if (t >= word.start && (!Number.isFinite(wordEnd) || t < wordEnd)) {
activeWordKey = `${activeIndex}-${i}`;
break;
}
}
}
}

if (activeWordKey !== currentWordKey) {
setActiveWord(activeWordKey);
}

};

});

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

	if (advancedPanel && !advancedPanel.hasAttribute("hidden")) {
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

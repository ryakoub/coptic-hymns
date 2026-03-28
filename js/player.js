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

const toggleLoopBtn = document.getElementById("toggleLoop");
const toggleScrollBtn = document.getElementById("toggleScroll");
const toggleCopticFontBtn = document.getElementById("toggleCopticFont");
const timestampsBox = document.getElementById("timestamps");

let repeatVerseEnabled = false;
let autoScrollEnabled = true;
let currentLineIndex = -1;
let currentLines = [];
let capturedTimes = [];
let loopTargetIndex = null;
let currentWordKey = null;

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

audio.src = `${base}/audio.mp3`;

fetch(`${base}/info.json`)
.then(r=>r.json())
.then(info=>{
document.getElementById("title").innerText = info.title;
document.getElementById("youtubeLink").href = info.youtube;
audio.src = info.audio || `${base}/audio.mp3`;
});

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
audio.currentTime = word.start;
audio.play();
currentLineIndex = index;
if (repeatVerseEnabled) {
loopTargetIndex = index;
}
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
audio.currentTime=line.start;
audio.play();
currentLineIndex = index;
if (repeatVerseEnabled) {
loopTargetIndex = index;
}
};

lyricsContainer.appendChild(div);
line.element=div;

});

audio.ontimeupdate=()=>{
const t=audio.currentTime;

if (repeatVerseEnabled && loopTargetIndex !== null && currentLines[loopTargetIndex]) {
const loopLine = currentLines[loopTargetIndex];
const loopNext = currentLines[loopTargetIndex + 1];
const loopEnd = loopNext ? loopNext.start : audio.duration;
if (Number.isFinite(loopEnd) && t >= loopEnd - 0.03) {
audio.currentTime = loopLine.start;
audio.play();
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
currentLines.forEach(x => x.element.classList.remove("active"));
currentLines[activeIndex].element.classList.add("active");
currentLineIndex = activeIndex;

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
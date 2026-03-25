const audio = document.getElementById("audio");
const lyricsContainer = document.getElementById("lyrics");

const params = new URLSearchParams(window.location.search);
const hymn = params.get("hymn");
const group = params.get("group") || "grades-3-4";
const level = params.get("level") || "level-1";

const toggleLoopBtn = document.getElementById("toggleLoop");
const toggleScrollBtn = document.getElementById("toggleScroll");
const copyTimestampsBtn = document.getElementById("copyTimestamps");
const timestampsBox = document.getElementById("timestamps");

let repeatVerseEnabled = false;
let autoScrollEnabled = true;
let currentLineIndex = -1;
let currentLines = [];
let capturedTimes = [];
let loopTargetIndex = null;

const base = `content/mahragan-keraza-2026/${group}/${level}/${hymn}`;

audio.src = `${base}/audio.mp3`;

fetch(`${base}/info.json`)
.then(r=>r.json())
.then(info=>{
document.getElementById("title").innerText = info.title;
document.getElementById("youtubeLink").href = info.youtube;
});

fetch(`${base}/lyrics.json`)
.then(r=>r.json())
.then(lines=>{
currentLines = lines;

lines.forEach((line, index)=>{

const div=document.createElement("div");
div.className="line";

div.innerHTML=
`<div class="coptic">${line.coptic}</div>
<div class="translation">${line.translations?.english || ""}</div>`;

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

copyTimestampsBtn?.addEventListener("click", async () => {
if (!capturedTimes.length) {
timestampsBox.textContent = "Timestamps: none captured yet.";
return;
}
const text = capturedTimes.join("\n");
try {
await navigator.clipboard.writeText(text);
timestampsBox.textContent = `Copied ${capturedTimes.length} timestamps to clipboard.\n\n${text}`;
} catch (err) {
timestampsBox.textContent = `Copy blocked by browser. Here are your timestamps:\n\n${text}`;
}
});

// Timestamp capture tool: Press "T" to log current time
document.addEventListener("keydown", function(e){
    if(e.key === "t" || e.key === "T"){
        const time = audio.currentTime.toFixed(2);
        capturedTimes.push(time);
        console.log(`Timestamp: ${time}`);
        if (timestampsBox) {
            timestampsBox.textContent = `Timestamps (${capturedTimes.length}):\n${capturedTimes.join("\n")}`;
        }
    }
});
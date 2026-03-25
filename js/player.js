const audio = document.getElementById("audio");
const lyricsContainer = document.getElementById("lyrics");

const params = new URLSearchParams(window.location.search);
const hymn = params.get("hymn");
const group = params.get("group") || "grades-3-4";
const level = params.get("level") || "level-1";

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

lines.forEach(line=>{

const div=document.createElement("div");
div.className="line";

div.innerHTML=
`<div class="coptic">${line.coptic}</div>
<div class="translation">${line.translations?.english || ""}</div>`;

div.onclick=()=>{
audio.currentTime=line.start;
audio.play();
};

lyricsContainer.appendChild(div);
line.element=div;

});

audio.ontimeupdate=()=>{
const t=audio.currentTime;

lines.forEach((l,i)=>{

const next=lines[i+1];

if(t>=l.start && (!next || t<next.start)){

lines.forEach(x=>x.element.classList.remove("active"));
l.element.classList.add("active");

}

});

};

});

// Timestamp capture tool: Press "T" to log current time
document.addEventListener("keydown", function(e){
    if(e.key === "t" || e.key === "T"){
        const time = audio.currentTime.toFixed(2);
        console.log(`Timestamp: ${time}`);
        // Display on page for easy copying
        const timestampDiv = document.getElementById("timestamps") || document.createElement("div");
        timestampDiv.id = "timestamps";
        timestampDiv.style.position = "fixed";
        timestampDiv.style.bottom = "10px";
        timestampDiv.style.right = "10px";
        timestampDiv.style.background = "rgba(0,0,0,0.8)";
        timestampDiv.style.color = "white";
        timestampDiv.style.padding = "10px";
        timestampDiv.style.borderRadius = "5px";
        timestampDiv.style.fontSize = "12px";
        timestampDiv.style.maxWidth = "200px";
        timestampDiv.innerHTML += `${time}<br>`;
        if (!document.getElementById("timestamps")) {
            document.body.appendChild(timestampDiv);
        }
        // Optional: alert for immediate feedback
        alert(`Timestamp recorded: ${time} seconds`);
    }
});
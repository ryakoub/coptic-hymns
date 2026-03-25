const audio = document.getElementById("audio");
const lyricsContainer = document.getElementById("lyrics");

const params = new URLSearchParams(window.location.search);
const hymn = params.get("hymn");

const base = `content/mahragan-keraza-2026/grades-1-2/level-1/${hymn}`;

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
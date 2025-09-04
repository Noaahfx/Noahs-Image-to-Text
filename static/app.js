const $ = (sel) => document.querySelector(sel);
const dropzone = $("#dropzone");
const input = $("#file-input");
const runBtn = $("#run-btn");
const clearBtn = $("#clear-btn");
const results = $("#results");

let files = [];
let progressInterval = null;

function renderFiles(){
  if(!files.length){ results.innerHTML = ""; return; }
  results.innerHTML = files.map((f,i)=>`
    <div class="result" data-idx="${i}">
      <div class="result__meta">
        <div class="result__name">${f.name}</div>
        <div class="result__actions">
          <button class="btn" data-copy>Copy text</button>
          <button class="btn" data-download>Download .txt</button>
          <button class="btn btn-ghost" data-remove>Remove</button>
        </div>
      </div>
      ${f.preview ? `<img class="result__img" src="${f.preview}" alt="">` : ""}
      <textarea placeholder="Extracted text will appear here...">${f.text || ""}</textarea>
    </div>
  `).join("");
}

function addFiles(fileList){
  for(const f of fileList){
    if(!f.type.startsWith("image/")) continue;
    const item = { file: f, name: f.name, text: "", preview: "" };
    const reader = new FileReader();
    reader.onload = (e)=>{ item.preview = e.target.result; renderFiles(); };
    reader.readAsDataURL(f);
    files.push(item);
  }
  renderFiles();
}

// --- Health pill in header ---
async function checkHealth(){
  const statusText = document.getElementById("status-text");
  const statusDot = document.querySelector(".status-dot");
  try {
    const r = await fetch("/api/health");
    const j = await r.json();
    if(j.ok){ statusText.textContent = "Ready"; statusDot.classList.remove("status-offline"); }
    else { statusText.textContent = "Unhealthy"; statusDot.classList.add("status-offline"); }
  } catch {
    statusText.textContent = "Offline";
    statusDot.classList.add("status-offline");
  }
}
checkHealth();

// --- Loader / progress ---
function setScreen(visible){
  const screen = document.getElementById("screen");
  if(visible){
    screen.classList.remove("hidden");
    startProgress();
  }else{
    stopProgress(() => screen.classList.add("hidden"));
  }
}
function startProgress(){
  const text = document.getElementById("progress-text");
  let progress = 0;
  text.textContent = "Extracting text… 0%";
  clearInterval(progressInterval);
  progressInterval = setInterval(()=>{
    if(progress < 95){
      progress += Math.floor(Math.random()*3)+1;
      if(progress > 95) progress = 95;
      text.textContent = `Extracting text… ${progress}%`;
    }
  }, 200);
}
function stopProgress(onDone){
  const text = document.getElementById("progress-text");
  clearInterval(progressInterval);
  text.textContent = "Extracting text… 100%";
  setTimeout(()=> { if(onDone) onDone(); }, 250); // brief finish flash
}

// --- Events ---
dropzone.addEventListener("click", ()=> input.click());
input.addEventListener("change", (e)=> addFiles(e.target.files));

dropzone.addEventListener("dragover", (e)=>{ e.preventDefault(); dropzone.classList.add("dragover"); });
dropzone.addEventListener("dragleave", ()=> dropzone.classList.remove("dragover"));
dropzone.addEventListener("drop", (e)=>{
  e.preventDefault();
  dropzone.classList.remove("dragover");
  addFiles(e.dataTransfer.files);
});

results.addEventListener("click", async (e)=>{
  const card = e.target.closest(".result");
  if(!card) return;
  const idx = Number(card.dataset.idx);
  const item = files[idx];
  if(e.target.matches("[data-remove]")){
    files.splice(idx,1); renderFiles(); return;
  }
  if(e.target.matches("[data-copy]")){
    const text = card.querySelector("textarea").value;
    await navigator.clipboard.writeText(text);
    e.target.textContent = "Copied!"; setTimeout(()=> e.target.textContent = "Copy text", 1200); return;
  }
  if(e.target.matches("[data-download]")){
    const text = card.querySelector("textarea").value;
    const blob = new Blob([text], {type: "text/plain;charset=utf-8"});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = (item.name.replace(/\.[^.]+$/, "") || "text") + ".txt";
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  }
});

runBtn.addEventListener("click", async (e)=>{
  e.preventDefault();
  if(!files.length) return;
  const fd = new FormData();
  for(const item of files) fd.append("files", item.file, item.name);

  setScreen(true);
  try{
    const res = await fetch("/api/ocr", { method: "POST", body: fd });
    if(!res.ok) throw new Error(`Server error ${res.status}`);
    const data = await res.json();
    const { items=[] } = data;
    items.forEach((r)=>{
      const idx = files.findIndex(f=>f.name===r.filename);
      if(idx>=0){
        files[idx].text = (r.text ?? "").trim() || (r.error ? `Error: ${r.error}` : "");
      }
    });
    renderFiles();
  }catch(err){
    console.error(err);
    alert("OCR failed. Check the backend log.");
  }finally{
    setScreen(false);
  }
});

clearBtn.addEventListener("click", (e)=>{
  e.preventDefault();
  files = []; input.value = ""; renderFiles();
});

document.getElementById("year").textContent = new Date().getFullYear();

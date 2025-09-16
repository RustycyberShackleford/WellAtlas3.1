// Frappe Gantt drill-down + filters + exports (gold theme + legend colors)
const qs = (s, r=document)=>r.querySelector(s);

let ganttGlobal, ganttSite, ganttJob;

function ganttify(el, items){
  if (!el) return null;
  el.innerHTML = ""; // reset
  if (!items || !items.length) { el.innerHTML = "<div style='padding:10px'>No items to display.</div>"; return null; }
  return new window.Gantt(el, items.map(i=>({
    id:i.id, name:i.name,
    start:i.start || new Date(), end:i.end || new Date(),
    progress:i.progress ?? 0, custom_class:i.custom_class || ""
  })), { view_mode: 'Month', language: 'en' });
}

async function fetchJSON(url){
  const res = await fetch(url);
  if (!res.ok) throw new Error(await res.text());
  return await res.json();
}

async function refreshJobs(){
  const params = new URLSearchParams();
  const fCategory = qs("#fCategory");
  const fStatus = qs("#fStatus");
  const fStart = qs("#fStart");
  const fEnd = qs("#fEnd");
  const fQuery = qs("#fQuery");
  if (fCategory.value) params.set("category", fCategory.value);
  if (fStatus.value) params.set("status", fStatus.value);
  if (fStart.value) params.set("start_after", fStart.value);
  if (fEnd.value) params.set("end_before", fEnd.value);
  if (fQuery.value) params.set("q", fQuery.value.trim());
  const rows = await fetchJSON(`/api/jobs?${params.toString()}`);
  renderGanttFromJobs(rows);
}

function renderGanttFromJobs(rows){
  const items = rows.filter(r=>r.start_date && r.end_date).map(r=>({
    id:`job-${r.id}`,
    name:`${r.site_name || "Site"} • Job ${r.job_number}`,
    start:r.start_date, end:r.end_date,
    progress:r.status==="Done"?100:r.status==="In Progress"?50:0,
    custom_class:`cat-${(r.job_category||'').toLowerCase()}`
  }));
  ganttGlobal = ganttify(qs("#ganttGlobal"), items);
}

async function openSiteGantt(siteId){
  const data = await fetchJSON(`/api/gantt/site/${siteId}`);
  ganttSite = ganttify(qs("#ganttSite"), data.items);
}

async function openJobGantt(jobId){
  const data = await fetchJSON(`/api/gantt/job/${jobId}`);
  ganttJob = ganttify(qs("#ganttJob"), data.items);
  const btn = qs("#btnTasksCsv");
  btn.href = `/api/export/job/${jobId}/tasks.csv`; btn.style.display = "";
}

qs("#btnExportJobs").onclick = ()=> window.location = "/api/export/jobs.csv";
qs("#fCategory").onchange = refreshJobs;
qs("#fStatus").onchange = refreshJobs;
qs("#fStart").onchange = refreshJobs;
qs("#fEnd").onchange = refreshJobs;
qs("#fQuery").oninput = (e)=>{ if(e.target.value.length===0 || e.target.value.length>2) refreshJobs(); };

// PNG export of visible gantt
qs("#btnGanttPng").onclick = () => {
  const el = qs("#ganttJob") || qs("#ganttSite") || qs("#ganttGlobal");
  const svg = el.querySelector("svg");
  if (!svg) return alert("Nothing to export");
  const xml = new XMLSerializer().serializeToString(svg);
  const svg64 = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(xml);
  const img = new Image();
  img.onload = () => {
    const canvas = document.createElement("canvas");
    canvas.width = img.width; canvas.height = img.height;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(img, 0, 0);
    const link = document.createElement("a");
    link.download = "gantt.png";
    link.href = canvas.toDataURL();
    link.click();
  };
  img.src = svg64;
};

// Initial load
refreshJobs();

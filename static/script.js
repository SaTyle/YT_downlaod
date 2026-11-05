"use strict";

const $ = (id) => document.getElementById(id);

const urlInput = $("url");
const fetchBtn = $("fetchBtn");
const msg = $("msg");
const videoCard = $("videoCard");
const thumb = $("thumb");
const titleEl = $("title");
const uploaderEl = $("uploader");
const durationEl = $("duration");
const qualitySel = $("quality");
const audioOnly = $("audioOnly");
const downloadBtn = $("downloadBtn");
const progressBox = $("progressBox");
const bar = $("bar");
const progressPct = $("progressPct");
const progressStat = $("progressStat");
const saveLink = $("saveLink");

let currentUrl = "";
let pollTimer = null;

function setMsg(text, type = "info") {
  msg.textContent = text;
  msg.className = "msg " + type;
}

function resetVideoCard() {
  videoCard.classList.add("hidden");
  progressBox.classList.add("hidden");
  saveLink.classList.add("hidden");
  downloadBtn.classList.remove("hidden");
  if (pollTimer) clearInterval(pollTimer);
}

async function fetchInfo() {
  const url = urlInput.value.trim();
  if (!url) {
    setMsg("Paste a YouTube link first.", "error");
    return;
  }

  resetVideoCard();
  setMsg("Fetching video info…", "info");
  fetchBtn.disabled = true;

  try {
    const res = await fetch("/api/info", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    const data = await res.json();

    if (!res.ok) {
      setMsg(data.error || "Could not fetch video.", "error");
      return;
    }

    currentUrl = url;
    thumb.src = data.thumbnail || "";
    titleEl.textContent = data.title || "Video";
    uploaderEl.textContent = data.uploader || "";
    durationEl.textContent = data.duration || "";

    // Fill quality dropdown with available heights.
    qualitySel.innerHTML = "";
    const heights = data.heights && data.heights.length ? data.heights : [720];
    heights.forEach((h) => {
      const opt = document.createElement("option");
      opt.value = h;
      const label =
        h >= 2160 ? `${h}p (4K)` : h >= 1440 ? `${h}p (2K)` : `${h}p`;
      opt.textContent = label;
      qualitySel.appendChild(opt);
    });
    // Default to 1080p if available, else the highest.
    const pref = heights.includes(1080) ? 1080 : heights[0];
    qualitySel.value = pref;

    videoCard.classList.remove("hidden");
    setMsg("", "info");
  } catch (err) {
    setMsg("Network error. Is the server running?", "error");
  } finally {
    fetchBtn.disabled = false;
  }
}

function syncQualityState() {
  qualitySel.disabled = audioOnly.checked;
  qualitySel.style.opacity = audioOnly.checked ? 0.5 : 1;
}

async function startDownload() {
  if (!currentUrl) return;

  downloadBtn.disabled = true;
  saveLink.classList.add("hidden");
  progressBox.classList.remove("hidden");
  bar.style.width = "0%";
  progressPct.textContent = "0%";
  progressStat.textContent = "Starting…";

  try {
    const res = await fetch("/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: currentUrl,
        height: parseInt(qualitySel.value, 10),
        audio_only: audioOnly.checked,
      }),
    });
    const data = await res.json();

    if (!res.ok) {
      setMsg(data.error || "Download failed to start.", "error");
      progressBox.classList.add("hidden");
      downloadBtn.disabled = false;
      return;
    }

    pollProgress(data.job_id);
  } catch (err) {
    setMsg("Network error while starting download.", "error");
    progressBox.classList.add("hidden");
    downloadBtn.disabled = false;
  }
}

function pollProgress(jobId) {
  if (pollTimer) clearInterval(pollTimer);

  pollTimer = setInterval(async () => {
    try {
      const res = await fetch(`/api/progress/${jobId}`);
      const job = await res.json();

      if (job.status === "downloading") {
        const pct = job.percent || 0;
        bar.style.width = pct + "%";
        progressPct.textContent = pct + "%";
        const parts = [];
        if (job.speed) parts.push(job.speed);
        if (job.eta) parts.push("ETA " + job.eta);
        progressStat.textContent = parts.join(" · ");
      } else if (job.status === "processing") {
        bar.style.width = "99%";
        progressPct.textContent = "99%";
        progressStat.textContent = "Merging video + audio…";
      } else if (job.status === "done") {
        clearInterval(pollTimer);
        bar.style.width = "100%";
        progressPct.textContent = "100%";
        progressStat.textContent = "Done!";
        downloadBtn.classList.add("hidden");
        saveLink.href = "/downloads/" + encodeURIComponent(job.filename);
        saveLink.textContent = "Save file ⬇";
        saveLink.classList.remove("hidden");
        downloadBtn.disabled = false;
        setMsg("Ready. Click “Save file” to download it.", "info");
      } else if (job.status === "error") {
        clearInterval(pollTimer);
        progressBox.classList.add("hidden");
        downloadBtn.disabled = false;
        setMsg("Error: " + (job.error || "download failed"), "error");
      }
    } catch (err) {
      clearInterval(pollTimer);
      downloadBtn.disabled = false;
      setMsg("Lost connection to server.", "error");
    }
  }, 600);
}

// Events
fetchBtn.addEventListener("click", fetchInfo);
urlInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") fetchInfo();
});
downloadBtn.addEventListener("click", startDownload);
audioOnly.addEventListener("change", syncQualityState);

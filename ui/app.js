const ERRORS = {
  auth: "API key was rejected — check it in ⚙",
  network: "No connection — check your internet",
  timeout: "Took too long — try again",
  bad_answer: "Couldn't read the answer — try again",
  other: "Something went wrong — try again",
};
const DIRS = ["tr-sr", "en-sr", "sr-en", "sr-tr"];

const $ = (id) => document.getElementById(id);
const text = $("text");
let direction = "tr-sr";
let requestId = 0;

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function rich(s) {
  return escapeHtml(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
}

function showStatus(message) {
  $("result").hidden = true;
  $("status").textContent = message;
}

function showSettings(show) {
  $("settings").hidden = !show;
  if (show) $("key").focus();
  else text.focus();
}

function setDirection(dir) {
  direction = dir;
  document.querySelectorAll(".dirs button").forEach((b) => b.classList.toggle("active", b.dataset.dir === dir));
  text.focus();
}

function render(r) {
  $("status").textContent = "";
  $("translation").innerHTML = rich(r.translation);
  $("grammar").textContent = r.grammar || "";
  $("grammar").hidden = !r.grammar;
  $("alts").textContent = r.alternatives.length ? "also: " + r.alternatives.join(", ") : "";
  $("alts").hidden = !r.alternatives.length;
  $("examples").innerHTML = r.examples
    .map((e) => `<li>${rich(e.serbian)}<span class="other">${rich(e.other)}</span></li>`)
    .join("");
  $("result").hidden = false;
}

async function lookup() {
  const value = text.value.trim();
  if (!value) return;
  const id = ++requestId;
  showStatus("Translating…");
  const out = await window.pywebview.api.translate(direction, value);
  if (id !== requestId) return;
  if (out.ok) render(out.result);
  else if (out.error === "no_key") { showStatus(""); showSettings(true); }
  else showStatus(ERRORS[out.error] || ERRORS.other);
}

async function saveKey() {
  const out = await window.pywebview.api.save_key($("key").value);
  if (out.ok) {
    $("key").value = "";
    $("key-msg").textContent = "";
    showSettings(false);
  } else {
    $("key-msg").textContent = "Please paste a valid key";
  }
}

window.addEventListener("pywebviewready", async () => {
  const state = await window.pywebview.api.get_state();
  setDirection(state.direction);
  showSettings(!state.has_key);
});

document.querySelectorAll(".dirs button").forEach((b) =>
  b.addEventListener("click", () => {
    setDirection(b.dataset.dir);
    window.pywebview.api.set_direction(b.dataset.dir);
  })
);

document.addEventListener("keydown", (e) => {
  if (e.ctrlKey && ["1", "2", "3", "4"].includes(e.key)) {
    e.preventDefault();
    const dir = DIRS[Number(e.key) - 1];
    setDirection(dir);
    window.pywebview.api.set_direction(dir);
  }
});

text.addEventListener("keydown", (e) => { if (e.key === "Enter") lookup(); });
$("key").addEventListener("keydown", (e) => { if (e.key === "Enter") saveKey(); });
$("save").addEventListener("click", saveKey);
$("gear").addEventListener("click", () => showSettings($("settings").hidden));

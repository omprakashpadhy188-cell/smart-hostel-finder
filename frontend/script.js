const API = "http://127.0.0.1:5000/api";
const picked = new Set();
const form = document.getElementById("filters");
const results = document.getElementById("results");
const statusEl = document.getElementById("status");
const dialog = document.getElementById("detail");
const money = n => "₹" + Number(n).toLocaleString("en-IN");
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

function setStatus(text, isError = false) { statusEl.textContent = text; statusEl.className = "status" + (isError ? " error" : ""); }

async function getJSON(url) {
  let res;
  try { res = await fetch(url); }
  catch { throw new Error("Cannot reach the server. Start it with: python app.py (inside the backend folder)."); }
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Something went wrong.");
  return data;
}

let latest = 0;
async function search() {
  const mine = ++latest;
  const params = new URLSearchParams();
  new FormData(form).forEach((v, k) => { if (String(v).trim()) params.set(k, String(v).trim()); });
  results.innerHTML = "";
  setStatus("Searching…");
  try {
    const { count, hostels } = await getJSON(`${API}/hostels?${params}`);
    if (mine !== latest) return;   // a newer search has started
    if (!count) { setStatus("No hostels match these filters. Try a higher budget or clear a filter."); return; }
    setStatus(`${count} hostel${count === 1 ? "" : "s"} found, best rated first.`);
    results.innerHTML = hostels.map(card).join("");
  } catch (e) { setStatus(e.message, true); }
}

function card(h) {
  return `<article class="card">
    <h3>${esc(h.name)}</h3>
    <p class="where">${esc(h.area)}, ${esc(h.city)} · near ${esc(h.nearest_institution)}</p>
    <div class="chips"><span>${esc(h.gender_type)}</span><span>${esc(h.food_type)} food</span><span>${h.mess_price ? "Mess" : "No mess"}</span><span>${h.laundry_price ? "Laundry" : "No laundry"}</span></div>
    <div class="price"><small>from</small> ${money(h.min_rent)}<small> /bed/month</small></div>
    <div class="meta"><span>Rating ${h.rating} (${h.review_count})</span><span>${h.distance_to_campus_km} km to campus</span></div>
    <label class="check pick"><input type="checkbox" data-pick="${h.hostel_id}" ${picked.has(h.hostel_id) ? "checked" : ""}> Add to compare</label>
    <button type="button" data-id="${h.hostel_id}">View rooms and prices</button>
  </article>`;
}

function roomTable(rooms, title) {
  if (!rooms.length) return `<h3>${title}</h3><p class="where">Not available</p>`;
  const rows = rooms.map(r => `<tr><td>${r.sharing_capacity} sharing</td><td>${money(r.monthly_rent)}</td><td>${money(r.security_deposit)}</td><td>${r.rooms_available}</td></tr>`).join("");
  return `<h3>${title}</h3><table><tr><th>Room</th><th>Rent / month</th><th>Deposit</th><th>Free rooms</th></tr>${rows}</table>`;
}

async function openDetail(id) {
  const body = document.getElementById("detailBody");
  body.innerHTML = "<p>Loading…</p>"; dialog.showModal();
  try {
    const h = await getJSON(`${API}/hostels/${id}`);
    body.innerHTML = `<h2>${esc(h.name)}</h2>
      <p class="where">${esc(h.area)}, ${esc(h.city)} · ${esc(h.gender_type)} · ${esc(h.food_type)} food</p>
      ${roomTable(h.rooms.filter(r => r.ac_type === "AC").sort((a, b) => a.sharing_capacity - b.sharing_capacity), "AC rooms")}
      ${roomTable(h.rooms.filter(r => r.ac_type === "Non-AC").sort((a, b) => a.sharing_capacity - b.sharing_capacity), "Non-AC rooms")}
      <h3>Extra monthly costs</h3>
      <p>Mess: ${h.mess_price ? money(h.mess_price) : "not available"}<br>Laundry: ${h.laundry_price ? money(h.laundry_price) : "not available"}</p>
      <h3>Amenities</h3><div class="chips">${h.amenities.map(a => `<span>${esc(a)}</span>`).join("")}</div>`;
  } catch (e) { body.innerHTML = `<p class="status error">${esc(e.message)}</p>`; }
}

form.addEventListener("submit", e => { e.preventDefault(); search(); });
let timer;
form.addEventListener("change", search);                       // selects update the results straight away
form.addEventListener("input", e => {                          // budget box waits until you stop typing
  if (e.target.name === "max_budget") { clearTimeout(timer); timer = setTimeout(search, 500); }
});
form.addEventListener("reset", () => setTimeout(search, 0));
results.addEventListener("click", e => { const b = e.target.closest("button[data-id]"); if (b) openDetail(b.dataset.id); });
document.getElementById("closeDetail").addEventListener("click", () => dialog.close());
search();

// ---- compare selection (2 to 4 hostels)
const cmpBar = document.getElementById("compareBar"), cmpText = document.getElementById("pickCount"), cmpGo = document.getElementById("goCompare");
function updateBar() {
  cmpBar.hidden = picked.size === 0;
  cmpText.textContent = picked.size < 2 ? `${picked.size} selected. Pick at least 2 to compare.` : `${picked.size} selected (up to 4).`;
  cmpGo.disabled = picked.size < 2;
}
results.addEventListener("change", e => {
  const box = e.target.closest("input[data-pick]"); if (!box) return;
  const id = Number(box.dataset.pick);
  if (box.checked && picked.size >= 4) { box.checked = false; setStatus("You can compare up to 4 hostels. Untick one first.", true); return; }
  box.checked ? picked.add(id) : picked.delete(id);
  updateBar();
});
cmpGo.addEventListener("click", () => { location.href = `compare.html?ids=${[...picked].join(",")}`; });
document.getElementById("clearPicks").addEventListener("click", () => { picked.clear(); document.querySelectorAll("input[data-pick]").forEach(b => b.checked = false); updateBar(); });

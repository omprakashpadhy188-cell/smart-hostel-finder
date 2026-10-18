const API = "http://127.0.0.1:5000/api";
const form = document.getElementById("prefs");
const results = document.getElementById("results");
const statusEl = document.getElementById("status");
const money = n => "₹" + Number(n).toLocaleString("en-IN");
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const setStatus = (t, err = false) => { statusEl.textContent = t; statusEl.className = "status" + (err ? " error" : ""); };

// weight sliders show their value
form.querySelectorAll(".range").forEach(l => {
  const input = l.querySelector("input"), out = l.querySelector("output");
  const show = () => out.textContent = input.value;
  input.addEventListener("input", show); show();
});

// amenity checkboxes come from the API
fetch(`${API}/amenities`).then(r => r.json()).then(({ amenities }) => {
  document.getElementById("amenityBox").innerHTML = amenities.map(a =>
    `<label class="check"><input type="checkbox" name="amenity" value="${esc(a)}"> ${esc(a)}</label>`).join("");
}).catch(() => { document.getElementById("amenityBox").textContent = "Could not load amenities. Is the server running?"; });

form.addEventListener("submit", async e => {
  e.preventDefault();
  const f = new FormData(form);
  if (!f.get("city")) return setStatus("Choose a city first.", true);
  if (!Number(f.get("max_budget")) || Number(f.get("max_budget")) < 1) return setStatus("Enter your maximum monthly rent, for example 6000.", true);

  const body = {
    city: f.get("city"), max_budget: Number(f.get("max_budget")),
    ac_preference: f.get("ac_preference"), food_pref: f.get("food_pref"),
    must_have_amenities: f.getAll("amenity"), top_n: 10,
    w_price: +f.get("w_price"), w_distance: +f.get("w_distance"), w_amenities: +f.get("w_amenities"), w_rating: +f.get("w_rating"),
  };
  if (f.get("gender")) body.gender = f.get("gender");
  if (f.get("sharing_capacity")) body.sharing_capacity = +f.get("sharing_capacity");
  if (f.get("max_distance_km")) body.max_distance_km = +f.get("max_distance_km");
  if (body.w_price + body.w_distance + body.w_amenities + body.w_rating === 0) return setStatus("Give at least one thing a weight above 0.", true);

  results.innerHTML = ""; setStatus("Ranking…");
  try {
    let res;
    try { res = await fetch(`${API}/recommend`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); }
    catch { throw new Error("Cannot reach the server. Start it with: python app.py (inside the backend folder)."); }
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Something went wrong.");
    if (!data.count) return setStatus(data.message);
    setStatus(`${data.count} hostel${data.count === 1 ? "" : "s"} match. Best match first.`);
    results.innerHTML = data.results.map(card).join("");
  } catch (err) { setStatus(err.message, true); }
});

const bar = (label, v) => `<div class="bar"><span>${label}</span><i><b style="width:${Math.round(v * 100)}%"></b></i></div>`;

function card(h, i) {
  const r = h.best_room, b = h.score_breakdown;
  return `<article class="card">
    <div class="rank"><span class="score">${Math.round(h.match_score)}<small>/100</small></span><h3>#${i + 1} ${esc(h.name)}</h3></div>
    <p class="where">${esc(h.area)}, ${esc(h.city)} · near ${esc(h.nearest_institution)}</p>
    <div class="price">${money(r.monthly_rent)}<small> /bed/month · ${r.sharing_capacity} sharing, ${esc(r.ac_type)}</small></div>
    <p class="where">About ${money(h.total_monthly_cost)} a month with the mess or laundry you asked for.</p>
    <div class="meta"><span>Rating ${h.rating}</span><span>${h.distance_to_campus_km} km to campus${h.within_preferred_distance ? "" : " (farther than you wanted)"}</span></div>
    <div class="chips">${h.matched_amenities.map(a => `<span>${esc(a)}</span>`).join("")}${h.missing_amenities.map(a => `<span class="miss">Missing: ${esc(a)}</span>`).join("")}</div>
    <div class="bars">${bar("Price", b.price)}${bar("Distance", b.distance)}${bar("Amenities", b.amenities)}${bar("Rating", b.rating)}</div>
  </article>`;
}

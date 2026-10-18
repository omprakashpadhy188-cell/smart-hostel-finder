const API = "http://127.0.0.1:5000/api";
const out = document.getElementById("out"), statusEl = document.getElementById("status");
const money = n => "₹" + Number(n).toLocaleString("en-IN");
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

async function load() {
  const ids = new URLSearchParams(location.search).get("ids");
  if (!ids) { statusEl.textContent = "No hostels selected. Go back to the search page and tick 'Add to compare' on 2 to 4 hostels."; return; }
  let res;
  try { res = await fetch(`${API}/compare?ids=${encodeURIComponent(ids)}`); }
  catch { statusEl.textContent = "Cannot reach the server. Start it with: python app.py (inside the backend folder)."; statusEl.className = "status error"; return; }
  const data = await res.json();
  if (!res.ok) { statusEl.textContent = data.error; statusEl.className = "status error"; return; }
  statusEl.textContent = `Comparing ${data.count} hostels. Highlighted cells are the best in each row.`;
  out.innerHTML = table(data);
}

const rooms = list => list.length ? list.map(r => `${r.sharing_capacity} sharing: ${money(r.monthly_rent)}`).join("<br>") : "Not available";

function table({ hostels, highlights: hl, common_amenities: common }) {
  const row = (label, cell, best) => `<tr><th scope="row">${label}</th>${hostels.map(h => `<td class="${best && best(h) ? "best" : ""}">${cell(h)}</td>`).join("")}</tr>`;
  return `<div class="cmp-scroll"><table class="cmp">
    <tr><th></th>${hostels.map(h => `<th scope="col"><h3>${esc(h.name)}</h3><span class="where">${esc(h.area)}, ${esc(h.city)}</span></th>`).join("")}</tr>
    ${row("Near", h => esc(h.nearest_institution))}
    ${row("Hostel for", h => esc(h.gender_type))}
    ${row("Food", h => esc(h.food_type))}
    ${row("Rating", h => `${h.rating} (${h.review_count} reviews)`, h => h.hostel_id === hl.best_rated)}
    ${row("Distance to campus", h => `${h.distance_to_campus_km} km`, h => h.hostel_id === hl.nearest_to_campus)}
    ${row("Lowest rent", h => h.min_rent ? money(h.min_rent) + " /bed/month" : "–", h => h.hostel_id === hl.cheapest_rent)}
    ${row("AC rooms", h => rooms(h.ac_options))}
    ${row("Non-AC rooms", h => rooms(h.non_ac_options))}
    ${row("Mess", h => h.mess_price ? money(h.mess_price) + " /month" : "Not available")}
    ${row("Laundry", h => h.laundry_price ? money(h.laundry_price) + " /month" : "Not available")}
    ${row("Amenities", h => h.amenities.length + " of 12<div class='chips'>" + h.amenities.map(a => `<span>${esc(a)}</span>`).join("") + "</div>", h => h.hostel_id === hl.most_amenities)}
  </table></div>
  <p class="where">${common.length ? "All of these have: " + common.map(esc).join(", ") + "." : "These hostels have no amenity in common."}</p>`;
}
load();

// Rewrite the now-playing section of README.md from the latest stats.fm stream.
// Logic mirrors the proven bjorkslefteyelash shrine implementation:
//   - /streams/current is "Not implemented" (400), so read /streams/recent.
//   - stats.fm's `endTime` is actually the track's START timestamp, so a track
//     counts as playing now while  now - start  <  durationMs + buffer.
//   - retry transient 5xx with backoff, fail fast on 4xx, bypass the 5-min cache.

import { readFile, writeFile } from "node:fs/promises";

const USER = process.env.STATSFM_USER || "cupidthatbtc";
const README = "README.md";
const START = "<!-- NOWPLAYING:START -->";
const END = "<!-- NOWPLAYING:END -->";
const LIVE_BUFFER = 90 * 1000;

function agoText(ts) {
  const then = new Date(ts).getTime();
  const s = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (s < 60) return "just now";
  const m = Math.floor(s / 60); if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60); if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d === 1) return "yesterday";
  if (d < 7) return `${d}d ago`;
  const dt = new Date(then);
  const opts = dt.getFullYear() === new Date().getFullYear()
    ? { month: "short", day: "numeric" }
    : { month: "short", day: "numeric", year: "numeric" };
  return dt.toLocaleDateString("en-US", opts).toLowerCase();
}

async function fetchRecent() {
  const url =
    `https://api.stats.fm/api/v1/users/${encodeURIComponent(USER)}` +
    `/streams/recent?limit=1&_=${Date.now()}`;
  let lastErr;
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const r = await fetch(url, {
        cache: "no-store",
        headers: { Accept: "application/json", "User-Agent": "cupidthatbtc-readme" },
      });
      if (r.ok) return (await r.json())?.items?.[0] ?? null;
      if (r.status < 500) throw new Error(`stats.fm ${r.status}`); // 4xx won't self-heal
      lastErr = new Error(`stats.fm ${r.status}`);                 // 5xx is transient
    } catch (e) { lastErr = e; }
    if (attempt < 2) await new Promise((res) => setTimeout(res, 400 * (attempt + 1)));
  }
  throw lastErr || new Error("stats.fm failed");
}

function render(stream) {
  const t = stream?.track;
  if (!t) return "—";
  const name = t.name ?? "unknown";
  const artist = (t.artists ?? []).map((a) => a.name).join(", ") || "unknown";
  const link = t.id ? `https://stats.fm/track/${t.id}` : null;
  const title = link ? `[${name}](${link})` : name;

  const start = stream.endTime ? new Date(stream.endTime).getTime() : 0;
  const dur = Number(t.durationMs) || 0;
  const elapsed = start ? Date.now() - start : Infinity;
  const liveWindow = dur ? dur + LIVE_BUFFER : 8 * 60 * 1000;
  const live = start > 0 && elapsed > -LIVE_BUFFER && elapsed < liveWindow;
  const endedTs = start ? (dur ? start + dur : start) : 0;

  if (live) return `now playing — **${title}** by ${artist}`;
  const when = endedTs ? ` <sub>· ${agoText(endedTs)}</sub>` : "";
  return `last played — **${title}** by ${artist}${when}`;
}

async function main() {
  let line;
  try {
    line = render(await fetchRecent());
  } catch (err) {
    console.error("now-playing fetch failed:", err.message);
    process.exit(0); // leave README untouched rather than wiping the section
  }

  const md = await readFile(README, "utf8");
  const re = new RegExp(`(${START})([\\s\\S]*?)(${END})`);
  if (!re.test(md)) {
    console.error("NOWPLAYING markers not found in README.md");
    process.exit(1);
  }
  const next = md.replace(re, `$1${line}$3`);
  if (next === md) {
    console.log("no change:", line);
    return;
  }
  await writeFile(README, next);
  console.log("updated:", line);
}

main();

#!/usr/bin/env python3
"""
SHA blog cover images — generated with Kie.ai (google/nano-banana).

Reads the blog RSS feed, and for every article that doesn't have a cover yet:
  1. builds a prompt (hand-written in blog-images/prompts.json, or auto from the title)
  2. asks Kie.ai to generate a 16:9 image
  3. saves it as blog-images/<article-slug>.jpg (1200x675, compressed JPEG)
  4. records it in blog-images/manifest.json (the website reads this file)

Env vars:
  KIE_API_KEY  (required)  — GitHub Actions secret
  FORCE        (optional)  — comma-separated slugs to regenerate, e.g. "article-3,article-7", or "all"
  MAX_NEW      (optional)  — safety cap on images per run (default 45)
"""
import io, json, os, re, sys, time, urllib.request, urllib.error
import xml.etree.ElementTree as ET
from PIL import Image

FEED = "https://blog.smarterhustleacademy.com/feed.xml"
API = "https://api.kie.ai/api/v1/jobs"
MODEL = "google/nano-banana"
OUT = "blog-images"
W, H = 1200, 675

KEY = os.environ.get("KIE_API_KEY", "").strip()
FORCE = {s.strip() for s in os.environ.get("FORCE", "").split(",") if s.strip()}
MAX_NEW = int(os.environ.get("MAX_NEW", "45") or 45)

STYLE = (
    "Modern editorial flat illustration with subtle paper grain texture. "
    "Strict limited palette: deep forest green #2D6A4F, warm gold #D4A017, "
    "cream #FAFAF5 and dark ink green #16241D, with small touches of soft sage. "
    "Clean composition, one clear focal point, generous negative space, soft shadows, "
    "friendly and optimistic mood, wide 16:9 blog header. Any people are diverse adults "
    "drawn in a simple stylized way. Absolutely no text, no words, no letters, no numbers, "
    "no logos, no watermarks, no captions anywhere in the image."
)

# Fallback scenes for NEW articles that don't have a hand-written prompt yet.
TOPICS = [
    (r"mortgage|housing|home price|rent", "a cozy house on a rising arrow with keys and a budget notebook"),
    (r"\bfed\b|interest rate|rate hike|rate cut", "a classic central bank building with a percent dial and stacked coins"),
    (r"treasury|debt|bond|deficit", "a treasury building with stacked bonds and a wallet in the foreground"),
    (r"grocer|food price|inflation|prices", "a grocery cart with a long receipt and rising price arrows"),
    (r"job|hiring|unemploy|wage|paycheck|income", "a paycheck, a calendar and a laptop on a kitchen table with a thoughtful adult"),
    (r"\bai\b|chatgpt|claude|automation|tool", "a laptop with a friendly AI sparkle helping build digital pages"),
    (r"email|list|newsletter", "a glowing inbox with envelopes flowing from a laptop"),
    (r"pinterest|tiktok|youtube|instagram|content|video|post|hook", "a creator scheduling short video cards on a calendar grid from a phone"),
    (r"bundle|product line", "several product boxes wrapped together into one bundle with a gold ribbon"),
    (r"price|pricing|\$", "a gold price tag on a digital guide with a small line of shoppers"),
    (r"niche|idea|validate|test", "a compass and magnifying glass over a glowing idea lightbulb"),
    (r"kdp|amazon|book|publish", "a stack of paperback books and journals beside a laptop"),
    (r"garden|homestead|grow", "a thriving raised-bed backyard garden with a small farm-stand table"),
    (r"trad|stock|chart|invest|crypto", "a calm beginner reading a simple chart on a tablet with a notebook"),
    (r"gumroad|etsy|payhip|store|sell", "a digital product box on a small online storefront counter with a shopping bag"),
]
DEFAULT_SCENE = "a laptop on a tidy desk producing a neat digital guide, with a coffee mug, plant and notebook"


def slug_of(link):
    m = re.search(r"([A-Za-z0-9_-]+)\.html?$", link.strip().rstrip("/"))
    if m:
        return m.group(1)
    return re.sub(r"[^a-z0-9]+", "-", link.lower()).strip("-")[-60:]


def http(url, data=None, method="GET"):
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json",
        "User-Agent": "sha-blog-images/1.0",
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def scene_for(title):
    t = title.lower()
    for pat, scene in TOPICS:
        if re.search(pat, t):
            return scene
    return DEFAULT_SCENE


def generate(prompt):
    body = json.dumps({"model": MODEL, "input": {
        "prompt": prompt, "output_format": "jpeg", "image_size": "16:9", "aspect_ratio": "16:9"}}).encode()
    res = json.loads(http(f"{API}/createTask", body, "POST"))
    if res.get("code") != 200:
        raise RuntimeError(f"createTask failed: {res}")
    task = res["data"]["taskId"]
    for _ in range(60):  # up to ~5 minutes
        time.sleep(5)
        info = json.loads(http(f"{API}/recordInfo?taskId={task}"))["data"]
        state = info.get("state")
        if state == "success":
            urls = json.loads(info["resultJson"]).get("resultUrls") or []
            if not urls:
                raise RuntimeError("no resultUrls")
            return urllib.request.urlopen(urls[0], timeout=120).read()
        if state == "fail":
            raise RuntimeError(f"task failed: {info.get('failMsg')}")
    raise RuntimeError("timed out")


def save_cover(raw, path):
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    # cover-crop to exactly 16:9, then resize
    tw = im.height * W / H
    if im.width > tw:
        x = int((im.width - tw) / 2); im = im.crop((x, 0, x + int(tw), im.height))
    else:
        th = im.width * H / W; y = int((im.height - th) / 2); im = im.crop((0, y, im.width, y + int(th)))
    im = im.resize((W, H), Image.LANCZOS)
    im.save(path, "JPEG", quality=82, optimize=True, progressive=True)


def main():
    if not KEY:
        sys.exit("KIE_API_KEY secret is missing.")
    os.makedirs(OUT, exist_ok=True)
    prompts = json.load(open(f"{OUT}/prompts.json")) if os.path.exists(f"{OUT}/prompts.json") else {}
    mpath = f"{OUT}/manifest.json"
    manifest = json.load(open(mpath)) if os.path.exists(mpath) else {}

    xml = urllib.request.urlopen(urllib.request.Request(FEED, headers={"User-Agent": "sha-blog-images/1.0"}), timeout=60).read()
    items = ET.fromstring(xml).findall(".//item")
    print(f"Feed has {len(items)} articles")

    made, failed = 0, []
    for it in items:
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        slug = slug_of(link)
        path = f"{OUT}/{slug}.jpg"
        forced = "all" in FORCE or slug in FORCE
        if os.path.exists(path) and not forced:
            manifest.setdefault(slug, {"img": f"/{path}", "title": title})
            continue
        if made >= MAX_NEW:
            print(f"Cap of {MAX_NEW} reached — the rest will be made next run."); break
        scene = prompts.get(slug) or scene_for(title)
        prompt = f"{STYLE} Scene: {scene}."
        print(f"→ {slug}: {title[:70]}")
        try:
            save_cover(generate(prompt), path)
            manifest[slug] = {"img": f"/{path}", "title": title}
            made += 1
            print(f"   saved {path}")
        except Exception as e:  # keep going; one failure shouldn't stop the batch
            failed.append(slug); print(f"   FAILED {slug}: {e}")

    with open(mpath, "w") as f:
        json.dump(dict(sorted(manifest.items(), key=lambda kv: -int(re.sub(r'\D', '', kv[0]) or 0))), f, indent=1)
    print(f"Done. New images: {made}. Failed: {failed or 'none'}")
    if failed and not made:
        sys.exit(1)


if __name__ == "__main__":
    main()

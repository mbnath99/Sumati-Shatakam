#!/usr/bin/env python3
"""
Renders one Sumati Satakam padyam as:
  - a 1080x1920 vertical video (Instagram Reel / YouTube Short / WhatsApp Status)
  - a 1080x1350 image card (WhatsApp Community / Instagram feed / Facebook)
  - caption text

CLI:  python render.py 12                 -> out/012.mp4, out/012.jpg, out/012.txt
      python render.py 12 --no-sound
      python render.py 12 --music my.mp3
"""
import argparse, json, math, os, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FPS, SR = 30, 44100
W, H = 1080, 1920

GOLD = (233, 184, 92)
GOLD_SOFT = (233, 184, 92, 70)
CREAM = (255, 244, 220)
CREAM_DIM = (240, 225, 200)
GREY = (190, 165, 140)

def load_config():
    with open(os.path.join(HERE, "config.json"), encoding="utf-8") as f:
        return json.load(f)

def load_book():
    with open(os.path.join(HERE, "data", "sumati.json"), encoding="utf-8") as f:
        return json.load(f)

# ------------------------------------------------------------------ fonts
_fc = {}
def font(name, size, weight=None):
    key = (name, size, weight)
    if key not in _fc:
        f = ImageFont.truetype(os.path.join(HERE, "fonts", name), size,
                               layout_engine=ImageFont.Layout.RAQM)
        if weight:
            try:
                axes = f.get_variation_axes()
                f.set_variation_by_axes([weight if a["name"] in (b"Weight", "Weight") else a["default"] for a in axes])
            except Exception:
                pass
        _fc[key] = f
    return _fc[key]

SERIF = "NotoSerifTelugu.ttf"
SANS = "NotoSansTelugu.ttf"
DISPLAY = "Suravaram.ttf"

def text_w(t, f):
    l, _, r, _ = f.getbbox(t)
    return r - l

def wrap(text, f, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if text_w(trial, f) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def text_sprite(lines, f, fill, line_h, align="center", width=None, shadow=True):
    """Render lines of text into a tight RGBA sprite (centered)."""
    asc, desc = f.getmetrics()
    width = width or max(text_w(l, f) for l in lines) + 20
    h = int(line_h * (len(lines) - 1) + asc + desc + 20)
    img = Image.new("RGBA", (width, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, l in enumerate(lines):
        y = 10 + i * line_h
        x = (width - text_w(l, f)) / 2 if align == "center" else 10
        d.text((x, y), l, font=f, fill=fill)
    if shadow:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sh.putalpha(img.getchannel("A").filter(ImageFilter.GaussianBlur(6)).point(lambda v: int(v * 0.7)))
        sh = Image.composite(Image.new("RGBA", img.size, (0, 0, 0, 255)), sh, sh.getchannel("A"))
        out = Image.new("RGBA", img.size, (0, 0, 0, 0))
        out.alpha_composite(sh, (0, 3)); out.alpha_composite(img)
        img = out
    return img

# ------------------------------------------------------------------ background art
def mandala(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = size / 2
    for r, w in [(0.48, 3), (0.44, 1), (0.30, 2), (0.27, 1), (0.14, 2)]:
        R = size * r
        d.ellipse([c - R, c - R, c + R, c + R], outline=GOLD + (60,), width=w)
    for k in range(24):  # outer petals
        a = 2 * math.pi * k / 24
        pts = []
        for t in np.linspace(-0.13, 0.13, 14):
            rr = size * (0.30 + 0.14 * math.cos(t / 0.13 * math.pi / 2))
            pts.append((c + rr * math.cos(a + t), c + rr * math.sin(a + t)))
        d.line(pts, fill=GOLD + (55,), width=2)
    for k in range(12):  # inner petals
        a = 2 * math.pi * k / 12
        pts = []
        for t in np.linspace(-0.25, 0.25, 14):
            rr = size * (0.14 + 0.13 * math.cos(t / 0.25 * math.pi / 2))
            pts.append((c + rr * math.cos(a + t), c + rr * math.sin(a + t)))
        d.line(pts, fill=GOLD + (60,), width=2)
    for k in range(48):  # dots
        a = 2 * math.pi * k / 48; R = size * 0.46
        x, y = c + R * math.cos(a), c + R * math.sin(a)
        d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=GOLD + (80,))
    return img

def base_background(w, h):
    y = np.linspace(0, 1, h)[:, None]
    x = np.linspace(-1, 1, w)[None, :]
    top = np.array([62, 14, 18]); bot = np.array([18, 4, 6])
    g = top[None, None, :] * (1 - y[..., None]) + bot[None, None, :] * y[..., None]
    glow = np.exp(-((x * 0.9) ** 2 + ((y - 0.33) * 2.2) ** 2))[..., None]
    g = g + glow * np.array([70, 38, 10])[None, None, :]
    vign = 1 - 0.45 * (x ** 2)[..., None] * np.ones_like(y)[..., None]
    g = np.clip(g * vign, 0, 255).astype(np.uint8)
    return Image.fromarray(g, "RGB").convert("RGBA")

def border(img, inset=34):
    d = ImageDraw.Draw(img)
    w, h = img.size
    d.rectangle([inset, inset, w - inset, h - inset], outline=GOLD + (150,), width=3)
    d.rectangle([inset + 12, inset + 12, w - inset - 12, h - inset - 12], outline=GOLD + (70,), width=1)
    for cx, cy in [(inset, inset), (w - inset, inset), (inset, h - inset), (w - inset, h - inset)]:
        d.regular_polygon((cx, cy, 13), 4, rotation=45, fill=GOLD + (200,))

def divider(d, cx, y, half=230, alpha=200):
    d.line([(cx - half, y), (cx - 22, y)], fill=GOLD + (alpha,), width=2)
    d.line([(cx + 22, y), (cx + half, y)], fill=GOLD + (alpha,), width=2)
    d.regular_polygon((cx, y, 11), 4, rotation=45, fill=GOLD + (alpha,))
    d.regular_polygon((cx - half - 8, y, 5), 4, rotation=45, fill=GOLD + (alpha,))
    d.regular_polygon((cx + half + 8, y, 5), 4, rotation=45, fill=GOLD + (alpha,))

# ------------------------------------------------------------------ layout shared by video + card
def build_layout(verse, cfg, W_, H_, card=False):
    """Returns sprites with positions. Shrinks fonts until the content fits between header and footer."""
    margin = 110
    max_w = W_ - 2 * margin
    cx = W_ // 2
    title = text_sprite([cfg.get("series_title", "సుమతీ శతకము")], font(DISPLAY, 86 if not card else 74), GOLD, 100)
    sub = text_sprite([f"పద్యం {verse['n']}"], font(SANS, 42, 500), CREAM_DIM, 50)
    foot = text_sprite([cfg["handle"]], font(SANS, 34, 600), GOLD, 40) if cfg.get("handle") else None
    credit = text_sprite([cfg["credit_line"]], font(SANS, 26, 400), GREY, 32, shadow=False) if cfg.get("credit_line") else None

    pos = {}
    y = 150 if not card else 95
    pos["title"] = (cx - title.width // 2, y); y += title.height - 6
    pos["sub"] = (cx - sub.width // 2, y); y += sub.height
    header_end = y
    bottom = H_ - (170 if not card else 150)
    if foot: pos["foot"] = (cx - foot.width // 2, bottom)
    if credit: pos["credit"] = (cx - credit.width // 2, bottom + (54 if not card else 48))
    region_top = header_end + (40 if not card else 20)
    region_bot = (bottom if foot else H_ - 120) - (40 if not card else 20)

    p_start = 70 if not card else 52
    b_start = 48 if not card else 36
    lsize = 54 if not card else 46
    for scale in [1 - 0.04 * i for i in range(13)]:
        psize, bsize = int(p_start * scale), int(b_start * scale)
        pf = font(SERIF, psize, 700)
        while max(text_w(l, pf) for l in verse["padyam"]) > max_w and psize > 30:
            psize -= 2; pf = font(SERIF, psize, 700)
        pline = int(psize * 1.75)
        bf = font(SANS, bsize, 400)
        bline = int(bsize * 1.62)
        bl = wrap(verse["bhavam"], bf, max_w)
        label = text_sprite(["భావం"], font(DISPLAY, int(lsize * max(scale, 0.8))), GOLD, 60)
        g = scale if not card else scale * 0.7
        block = [("div1", int(54 * g))] + [(f"p{i}", pline) for i in range(4)] + \
                [("pad_after", int(40 * g)), ("div2", int(50 * g)), ("label", label.height + 6),
                 ("bhavam", int(bline * (len(bl) - 1) + sum(bf.getmetrics()) + 20))]
        block_h = sum(h for _, h in block)
        if block_h <= region_bot - region_top:
            break
    pad_lines = [text_sprite([l], pf, CREAM, pline) for l in verse["padyam"]]
    bhavam = text_sprite(bl, bf, CREAM_DIM, bline, width=max_w + 20)
    y = region_top + max(0, (region_bot - region_top - block_h) * (0.42 if not card else 0.5))
    y = int(y)
    for key, h in block:
        if key in ("div1", "div2"): pos[key] = y + h // 3 if key == "div2" else y
        elif key == "label": pos[key] = (cx - label.width // 2, y)
        elif key == "bhavam": pos[key] = (cx - bhavam.width // 2, y)
        elif key.startswith("p") and key != "pad_after": pos[key] = (cx - pad_lines[int(key[1])].width // 2, y)
        y += h
    sprites = dict(title=title, sub=sub, label=label, bhavam=bhavam, foot=foot, credit=credit)
    for i, s in enumerate(pad_lines): sprites[f"p{i}"] = s
    sprites["_meta"] = dict(pf=pf, pline=pline, bf=bf, bline=bline, bl=bl, bw=max_w + 20)
    return sprites, pos

def with_alpha(sprite, a):
    if a >= 1: return sprite
    s = sprite.copy()
    s.putalpha(sprite.getchannel("A").point(lambda v: int(v * a)))
    return s

def ease(x):
    x = min(1, max(0, x)); return 1 - (1 - x) ** 3

# ------------------------------------------------------------------ image card
def render_card(verse, cfg, out_path):
    CW, CH = 1080, 1350
    img = base_background(CW, CH)
    m = mandala(1100)
    img.alpha_composite(m, ((CW - 1100) // 2, int(CH * 0.33) - 550))
    border(img)
    sprites, pos = build_layout(verse, cfg, CW, CH, card=True)
    d = ImageDraw.Draw(img)
    for k, s in sprites.items():
        if isinstance(s, Image.Image) and k in pos: img.alpha_composite(s, pos[k])
    divider(d, CW // 2, pos["div1"]); divider(d, CW // 2, pos["div2"], half=160)
    img.convert("RGB").save(out_path, quality=92)

# ------------------------------------------------------------------ typewriter helpers
_MARKS = set(range(0x0C00, 0x0C05)) | set(range(0x0C3C, 0x0C57)) | {0x0C62, 0x0C63, 0x200C, 0x200D}
_VIRAMA = 0x0C4D

def aksharas(text):
    """Split Telugu text into aksharas (consonant clusters + vowel signs), so a conjunct like
    'క్ష' or 'శ్రీ' appears as one letter instead of broken halves."""
    out = []
    for ch in text:
        cp = ord(ch)
        if out and (cp in _MARKS or ord(out[-1][-1]) == _VIRAMA and 0x0C15 <= cp <= 0x0C39):
            out[-1] += ch
        else:
            out.append(ch)
    return out

def typed_sprite(full, prefix, f, fill, width, line_h):
    """Sprite of `prefix` drawn exactly where it sits inside the centred `full` line."""
    asc, desc = f.getmetrics()
    img = Image.new("RGBA", (width, asc + desc + 20), (0, 0, 0, 0))
    x0 = (width - text_w(full, f)) / 2
    if prefix:
        ImageDraw.Draw(img).text((x0, 10), prefix, font=f, fill=fill)
        sh = Image.new("RGBA", img.size, (0, 0, 0, 255))
        sh.putalpha(img.getchannel("A").filter(ImageFilter.GaussianBlur(6)).point(lambda v: int(v * 0.7)))
        out = Image.new("RGBA", img.size, (0, 0, 0, 0))
        out.alpha_composite(sh, (0, 3)); out.alpha_composite(img)
        img = out
    caret_x = x0 + (f.getbbox(prefix)[2] if prefix else 0) + 6
    return img, caret_x

# ------------------------------------------------------------------ video
def render_video(verse, cfg, out_path, sound=None):
    sprites, pos = build_layout(verse, cfg, W, H)
    meta = sprites["_meta"]
    bg = base_background(W, H)
    border(bg)
    mand = mandala(1300)
    mcy = int(H * 0.40)
    bg_lo, bg_hi = bg.copy(), bg.copy()            # mandala at two strengths; frames blend between
    bg_lo.alpha_composite(with_alpha(mand, 0.45), ((W - 1300) // 2, mcy - 650))
    bg_hi.alpha_composite(mand, ((W - 1300) // 2, mcy - 650))
    bg_lo, bg_hi = bg_lo.convert("RGB"), bg_hi.convert("RGB")

    anim = cfg.get("text_animation", "typewriter")
    tcfg = cfg.get("typing", {})
    p_cps = tcfg.get("padyam_letters_per_second", 9)
    b_cps = tcfg.get("bhavam_letters_per_second", 16)
    max_total = cfg.get("max_video_seconds", 58)
    T_title = 0.4

    # ---- typing units: 4 padyam lines, then each wrapped bhavam line
    units = []
    for i, line in enumerate(verse["padyam"]):
        x, y = pos[f"p{i}"]
        units.append(dict(kind="p", text=line, ak=aksharas(line), f=meta["pf"], fill=CREAM,
                          width=sprites[f"p{i}"].width, xy=(x, y)))
    bx, by = pos["bhavam"]
    for j, line in enumerate(meta["bl"]):
        units.append(dict(kind="b", text=line, ak=aksharas(line), f=meta["bf"], fill=CREAM_DIM,
                          width=meta["bw"], xy=(bx, by + j * meta["bline"])))
    n_b = sum(len(u["ak"]) for u in units if u["kind"] == "b")
    hold = max(4.0, n_b / 40.0)

    t = 1.4
    for u in units:
        if u["kind"] == "p":
            u["start"], u["cps"] = t, p_cps
            t += len(u["ak"]) / p_cps + 0.35
    T_bhavam = t + 0.4                                    # divider + 'భావం' label fade in here
    t_b0 = T_bhavam + 0.8
    budget = max_total - t_b0 - hold - 1.0
    if n_b / b_cps > budget > 0:                          # long meaning: type faster to fit
        b_cps = n_b / budget
    t = t_b0
    for u in units:
        if u["kind"] == "b":
            u["start"], u["cps"] = t, b_cps
            t += len(u["ak"]) / b_cps + 0.08
    total = min(t + hold + 1.0, max_total) if anim == "typewriter" else None
    if anim != "typewriter":                              # classic: fade in line by line
        T_lines, line_gap = 1.6, 1.5
        T_bhavam = T_lines + 4 * line_gap + 0.4
        total = min(T_bhavam + max(7.0, len(verse["bhavam"]) / 15.0) + 2.0, max_total)
    nframes = int(total * FPS)

    cache = {}
    def sprite_for(ui, k):
        key = (ui, k)
        if key not in cache:
            u = units[ui]
            cache[key] = typed_sprite(u["text"], "".join(u["ak"][:k]), u["f"], u["fill"], u["width"], 0)
        return cache[key]

    tmp = out_path + ".v.mp4"
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
                             "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                             "-movflags", "+faststart", tmp], stdin=subprocess.PIPE)
    for fi in range(nframes):
        t = fi / FPS
        breathe = (0.5 + 0.5 * math.sin(t * 0.9 - 1.5)) * ease(t / 1.5)
        fr = Image.blend(bg_lo, bg_hi, breathe).convert("RGBA")
        d = ImageDraw.Draw(fr)
        a = ease((t - T_title) / 0.8)
        for k in ("title", "sub"):
            if a > 0: fr.alpha_composite(with_alpha(sprites[k], a), pos[k])
        if a > 0: divider(d, W // 2, pos["div1"], alpha=int(200 * a))
        a = ease((t - T_bhavam) / 0.7)
        if a > 0:
            divider(d, W // 2, pos["div2"], half=int(160 * a) + 1, alpha=int(200 * a))
            fr.alpha_composite(with_alpha(sprites["label"], a), pos["label"])

        if anim == "typewriter":
            for ui, u in enumerate(units):
                if t < u["start"]: continue
                k = min(len(u["ak"]), int((t - u["start"]) * u["cps"]) + 1)
                img, caret_x = sprite_for(ui, k)
                fr.alpha_composite(img, u["xy"])
                typing = k < len(u["ak"]) or (ui + 1 < len(units) and t < units[ui + 1]["start"] and units[ui + 1]["kind"] == u["kind"])
                if typing and (k < len(u["ak"]) or int(t * 3) % 2 == 0):   # caret, blinking during pauses
                    asc, desc = u["f"].getmetrics()
                    x = u["xy"][0] + caret_x; y0 = u["xy"][1] + 10 + asc * 0.15; y1 = u["xy"][1] + 10 + asc + desc * 0.3
                    d.line([(x, y0), (x, y1)], fill=GOLD + (230,), width=4)
        else:
            for i in range(4):
                a = ease((t - (1.6 + i * 1.5)) / 0.7)
                if a > 0:
                    x, y = pos[f"p{i}"]
                    fr.alpha_composite(with_alpha(sprites[f"p{i}"], a), (x, int(y + (1 - a) * 22)))
            a = ease((t - T_bhavam - 0.3) / 0.9)
            if a > 0:
                x, y = pos["bhavam"]
                fr.alpha_composite(with_alpha(sprites["bhavam"], a), (x, int(y + (1 - a) * 18)))

        a = ease((t - 1.0) / 1.0)
        for k in ("foot", "credit"):
            if sprites.get(k) is not None and a > 0:
                fr.alpha_composite(with_alpha(sprites[k], a), pos[k])
        fade = min(1, (total - t) / 0.8)
        frame = fr.convert("RGB")
        if fade < 1:
            frame = Image.blend(Image.new("RGB", (W, H)), frame, max(0, fade))
        proc.stdin.write(frame.tobytes())
    proc.stdin.close(); proc.wait()
    sound = sound or {}
    if sound.get("enabled", True):
        wav = out_path + ".a.wav"
        make_audio(wav, total, sound)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-i", wav, "-c:v", "copy", "-c:a", "aac",
                        "-b:a", "160k", "-shortest", "-movflags", "+faststart", out_path], check=True)
        os.remove(wav); os.remove(tmp)
    else:
        os.replace(tmp, out_path)
    return total

# ------------------------------------------------------------------ audio: tanpura drone + temple bell
def _pluck(f0, dur, amp):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.zeros(n)
    for k in range(1, 16):
        if f0 * k > 9000: break
        # jawari: upper harmonics bloom a little after the attack and shimmer
        bloom = 1 - np.exp(-t * (2.5 + 0.4 * k))
        shimmer = 1 + 0.25 * np.sin(2 * np.pi * (0.35 + 0.07 * k) * t + k)
        s += (1 / k ** 0.9) * np.sin(2 * np.pi * f0 * k * t + k) * (bloom if k > 2 else 1) * shimmer
    env = np.exp(-t / 2.4) * (1 - np.exp(-t * 120))
    return s * env * amp

def tanpura(total, sa=146.83):
    n = int(total * SR); out = np.zeros(n + SR * 6)
    cycle = [(sa * 0.75, 0.9), (sa * 2, 0.75), (sa * 2, 0.75), (sa, 1.0)]  # Pa(low) Sa' Sa' Sa
    step = 0.62
    t = 0.0; i = 0
    while t < total:
        f0, a = cycle[i % 4]
        p = _pluck(f0, 5.0, a)
        s0 = int(t * SR); out[s0:s0 + len(p)] += p
        t += step if i % 4 != 3 else step * 1.6
        i += 1
    out = out[:n]
    # simple room reverb (three feedback combs)
    from scipy.signal import lfilter
    rev = np.zeros_like(out)
    for dl, g in ((1557, 0.55), (2203, 0.5), (3119, 0.45)):
        a = np.zeros(dl + 1); a[0] = 1; a[dl] = -g
        rev += lfilter([1.0], a, out)
    return out * 0.6 + rev * 0.15

def bell(dur=6.0, f=523.0):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.zeros(n)
    for ratio, amp, dec in ((0.5, 0.5, 2.5), (1, 1, 3.5), (2.76, 0.6, 1.8), (5.4, 0.35, 1.0), (8.93, 0.2, 0.6)):
        s += amp * np.sin(2 * np.pi * f * ratio * t) * np.exp(-t / dec)
    return s * (1 - np.exp(-t * 300))

def make_audio(path, total, opt):
    n = int(total * SR)
    mix = np.zeros(n)
    music = opt.get("music", "tanpura")
    vol = opt.get("music_volume", 0.6)
    if music == "tanpura":
        mix += tanpura(total) * vol
    elif music and music != "none":
        mp = music if os.path.isabs(music) else os.path.join(HERE, music)
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", mp, "-t", str(total), "-f", "s16le", "-ac", "1",
                              "-ar", str(SR), "-"], capture_output=True, check=True).stdout
        m = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768
        m = m[:n]
        mix[:len(m)] += m * vol * 3
    if opt.get("bell", True):
        b = bell()[:n] * 0.9
        mix[:len(b)] += b
    # fade in/out
    fi, fo = int(0.3 * SR), int(1.2 * SR)
    mix[:fi] *= np.linspace(0, 1, fi); mix[-fo:] *= np.linspace(1, 0, fo)
    peak = np.max(np.abs(mix)) or 1
    pcm = (mix / peak * 0.8 * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())

# ------------------------------------------------------------------ captions
def captions(verse, cfg, book):
    n = verse["n"]
    tags = " ".join(cfg.get("hashtags", []))
    padyam = "\n".join(verse["padyam"])
    head = f"🙏 {book['title']} – పద్యం {n}"
    credit = cfg.get("credit_line", "")
    body = f"{head}\n\n{padyam}\n\nభావం:\n{verse['bhavam']}\n\n— {book['author']}"
    if credit: body += f"\n{credit}"
    long_caption = body + (f"\n\n{tags}" if tags else "")
    first = verse["padyam"][0].rstrip(",.!?")
    yt_title = f"సుమతీ శతకం పద్యం {n} | {first} | Sumati Satakam #Shorts"[:100]
    whatsapp = body
    return dict(instagram=long_caption[:2200], youtube_title=yt_title,
                youtube_description=long_caption[:4900], whatsapp=whatsapp)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int)
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--no-sound", action="store_true")
    ap.add_argument("--music", help="tanpura | none | path to mp3")
    ap.add_argument("--no-bell", action="store_true")
    a = ap.parse_args()
    cfg, book = load_config(), load_book()
    verse = next(v for v in book["verses"] if v["n"] == a.n)
    os.makedirs(a.out, exist_ok=True)
    stem = os.path.join(a.out, f"{a.n:03d}")
    snd = dict(cfg.get("sound", {}))
    if a.no_sound: snd["enabled"] = False
    if a.music: snd["music"] = a.music
    if a.no_bell: snd["bell"] = False
    render_card(verse, cfg, stem + ".jpg")
    dur = render_video(verse, cfg, stem + ".mp4", snd)
    c = captions(verse, cfg, book)
    with open(stem + ".txt", "w", encoding="utf-8") as f:
        f.write(c["instagram"])
    print(f"padyam {a.n}: {dur:.1f}s video -> {stem}.mp4 / .jpg / .txt")

if __name__ == "__main__":
    main()

"""Parse Tesseract OCR text of the Sumati Satakam PDF into a draft JSON (to be proofread)."""
import json, re, sys
src, out = sys.argv[1], sys.argv[2]
lines = [l.rstrip() for l in open(src, encoding="utf-8")]
num_re = re.compile(r"^\s*([0-9౦-౯]{1,3})\s*[.,]\s*(.+)$")
tel2ascii = str.maketrans("౦౧౨౩౪౫౬౭౮౯", "0123456789")
verses, cur, expected = [], None, 1
for l in lines:
    m = num_re.match(l)
    if m:
        n = int(m.group(1).translate(tel2ascii)[-len(str(expected)):] or 0) if False else None
        raw = m.group(1).translate(tel2ascii)
        # accept if it matches the expected number (OCR sometimes doubles a digit, e.g. '3౩6' -> '336')
        if raw == str(expected) or raw.endswith(str(expected)[-1]) and len(raw) >= len(str(expected)) and raw[-len(str(expected)):] == str(expected) or raw.replace(raw[0], "", 1) == str(expected):
            cur = {"n": expected, "padyam": [m.group(2).strip()], "bhavam": []}
            verses.append(cur); expected += 1
            continue
    if cur is None or not l.strip() or re.fullmatch(r"\s*\d+\s*", l):
        continue
    if len(cur["padyam"]) < 4 and not cur["bhavam"]:
        cur["padyam"].append(l.strip())
    else:
        cur["bhavam"].append(l.strip())
for v in verses:
    v["bhavam"] = " ".join(v["bhavam"])
print(len(verses), "verses; last =", verses[-1]["n"])
json.dump(verses, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

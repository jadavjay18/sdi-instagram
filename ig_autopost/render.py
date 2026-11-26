"""Render Super Deals India carousel slides (1080x1350 JPEG) with Pillow.

Layout matches the approved canvas design:
  - Cover (dark): green pill tag, big orange kicker (optional strike), white title, grey subtitle
  - Point slides (cream): big orange number, heading, body, green "Pro tip" box
  - CTA slide (dark): "Ye post kaam ki lagi?" + Save / Share / Link-in-bio rows
Every slide: logo tile + "Super Deals India" header, n/N counter, footer.
"""
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent.parent
FONTS = BASE / "fonts"
LOGO = BASE / "assets" / "logo.png"
LOGO_B64 = BASE / "assets" / "logo.b64"

W, H = 1080, 1350
PAD_X, PAD_TOP, PAD_BOTTOM = 80, 64, 60
CONTENT_W = W - 2 * PAD_X

DARK = (21, 22, 26)
CREAM = (251, 243, 232)
ORANGE = (255, 122, 0)
ORANGE_DEEP = (217, 96, 10)
GREEN = (46, 154, 58)
GREEN_LIGHT = (92, 198, 106)
GREEN_TEXT = (31, 107, 40)
GREEN_BG = (228, 243, 230)
WHITE = (255, 255, 255)
GREY_ON_DARK = (201, 203, 209)
GREY_ON_CREAM = (90, 90, 90)
BODY_ON_CREAM = (58, 58, 58)

EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F900-\U0001F9FF"
    "\U00002B00-\U00002BFF️‍]+"
)


def clean(text: str) -> str:
    """Slides can't render emoji with these fonts, so strip them."""
    return re.sub(r"\s{2,}", " ", EMOJI_RE.sub("", text or "")).strip()


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    files = {
        "head": "Poppins-Bold.ttf",
        "head_italic": "Poppins-BoldItalic.ttf",
        "head_medium": "Poppins-Medium.ttf",
        "body": "Inter-Regular.otf",
        "body_medium": "Inter-Medium.otf",
        "body_semibold": "Inter-SemiBold.otf",
    }
    fallback = {"body": "Poppins-Medium.ttf", "body_medium": "Poppins-Medium.ttf",
                "body_semibold": "Poppins-Bold.ttf", "head_italic": "Poppins-Bold.ttf"}
    path = FONTS / files[name]
    if not path.exists() and name in fallback:
        path = FONTS / fallback[name]
    return ImageFont.truetype(str(path), size)


def load_logo():
    import base64
    import io
    if LOGO.exists():
        return Image.open(LOGO)
    if LOGO_B64.exists():
        return Image.open(io.BytesIO(base64.b64decode(LOGO_B64.read_text())))
    return None


def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=fnt) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


class Block:
    """A wrapped text block that can be measured, then drawn."""

    def __init__(self, draw, text, fname, size, color, max_w=CONTENT_W, lh=1.2,
                 max_lines=None, min_size=None, strike=None):
        self.draw, self.color, self.strike = draw, color, strike
        size_now = size
        while True:
            self.font = font(fname, size_now)
            self.lines = wrap(draw, text, self.font, max_w)
            fits = max_lines is None or len(self.lines) <= max_lines
            if fits or not min_size or size_now <= min_size:
                break
            size_now -= 4
        self.size = size_now
        self.line_h = int(size_now * lh)
        self.height = self.line_h * len(self.lines)

    def draw_at(self, x, y):
        for i, line in enumerate(self.lines):
            ly = y + i * self.line_h
            self.draw.text((x, ly), line, font=self.font, fill=self.color)
            if self.strike:
                tw = self.draw.textlength(line, font=self.font)
                sy = ly + int(self.size * 0.62)
                self.draw.rectangle([x, sy - 7, x + tw, sy + 7], fill=self.strike)
        return y + self.height


def rounded(draw, box, r, fill):
    draw.rounded_rectangle(box, radius=r, fill=fill)


def header(img, draw, n, total, dark):
    tile = 104
    rounded(draw, [PAD_X, PAD_TOP, PAD_X + tile, PAD_TOP + tile], 24, CREAM)
    src = load_logo()
    if src is not None:
        logo = src.convert("RGBA").resize((tile, tile), Image.LANCZOS)
        mask = Image.new("L", (tile, tile), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, tile, tile], radius=24, fill=255)
        img.paste(logo, (PAD_X, PAD_TOP), mask)
    f = font("head", 32)
    tx = PAD_X + tile + 20
    draw.text((tx, PAD_TOP + 14), "Super Deals", font=f, fill=WHITE if dark else DARK)
    draw.text((tx, PAD_TOP + 52), "India", font=f, fill=GREEN_LIGHT if dark else GREEN)
    # counter pill
    cf = font("head_medium", 28)
    label = f"{n}/{total}"
    tw = draw.textlength(label, font=cf)
    pill_w, pill_h = int(tw) + 52, 56
    px = W - PAD_X - pill_w
    py = PAD_TOP + (tile - pill_h) // 2
    pill_fill = (44, 45, 49) if dark else (234, 226, 216)
    rounded(draw, [px, py, px + pill_w, py + pill_h], 28, pill_fill)
    draw.text((px + 26, py + 10), label, font=cf, fill=GREY_ON_DARK if dark else GREY_ON_CREAM)
    return PAD_TOP + tile


def bookmark_icon(draw, x, y, size, color, width=3):
    s = size
    pts = [(x + s * .25, y + s * .12), (x + s * .75, y + s * .12), (x + s * .75, y + s * .88),
           (x + s * .5, y + s * .7), (x + s * .25, y + s * .88), (x + s * .25, y + s * .12)]
    draw.line(pts, fill=color, width=width, joint="curve")


def arrow_icon(draw, x, y, size, color, width=4):
    m = y + size / 2
    draw.line([(x + size * .2, m), (x + size * .8, m)], fill=color, width=width)
    draw.line([(x + size * .55, y + size * .25), (x + size * .8, m), (x + size * .55, y + size * .75)],
              fill=color, width=width, joint="curve")


def footer(draw, n, total, dark):
    grey = GREY_ON_DARK if dark else GREY_ON_CREAM
    f = font("body_medium", 28)
    y = H - PAD_BOTTOM - 36
    bookmark_icon(draw, PAD_X, y, 34, grey)
    draw.text((PAD_X + 44, y), "Save karo, baad mein kaam aayega", font=f, fill=grey)
    rf = font("head_medium", 30)
    label = "Swipe karo" if n < total else "Link in bio"
    tw = draw.textlength(label, font=rf)
    if n < total:
        arrow_icon(draw, W - PAD_X - 36, y - 1, 38, ORANGE)
        draw.text((W - PAD_X - 48 - tw, y - 2), label, font=rf, fill=ORANGE)
    else:
        draw.text((W - PAD_X - tw, y - 2), label, font=rf, fill=ORANGE)
    return y


def layout_center(top, bottom, items, gap=28):
    """items: list of (height, draw_fn(y)). Vertically centre the stack."""
    total = sum(h for h, _ in items) + gap * (len(items) - 1)
    y = top + max(0, (bottom - top - total) // 2)
    for h, fn in items:
        fn(y)
        y += h + gap
    return total


def new_slide(dark):
    img = Image.new("RGB", (W, H), DARK if dark else CREAM)
    return img, ImageDraw.Draw(img)


def render_cover(c, n, total):
    img, d = new_slide(True)
    top = header(img, d, n, total, True) + 40
    bottom = footer(d, n, total, True) - 40

    tag_f = font("head_medium", 28)
    tag = clean(c["pillar"])
    tag_w = int(d.textlength(tag, font=tag_f)) + 56

    def draw_tag(y):
        rounded(d, [PAD_X, y, PAD_X + tag_w, y + 56], 28, GREEN)
        d.text((PAD_X + 28, y + 10), tag, font=tag_f, fill=WHITE)

    items = [(56, draw_tag)]
    kicker = clean(c.get("cover_kicker", ""))
    if kicker:
        kb = Block(d, kicker, "head_italic", 176, ORANGE, lh=1.05, max_lines=1, min_size=96,
                   strike=WHITE if c.get("cover_strike") else None)
        items.append((kb.height, lambda y: kb.draw_at(PAD_X, y)))
    tb = Block(d, clean(c["cover_title"]), "head", 92, WHITE, lh=1.1, max_lines=3, min_size=64)
    items.append((tb.height, lambda y: tb.draw_at(PAD_X, y)))
    sb = Block(d, clean(c["cover_sub"]), "body", 42, GREY_ON_DARK, lh=1.4, max_lines=3, min_size=32)
    items.append((sb.height, lambda y: sb.draw_at(PAD_X, y)))
    layout_center(top, bottom, items)
    return img


def render_point(p, idx, n, total):
    img, d = new_slide(False)
    top = header(img, d, n, total, False) + 40
    bottom = footer(d, n, total, False) - 40

    num = Block(d, f"{idx:02d}", "head", 160, ORANGE_DEEP, lh=1.0)
    hb = Block(d, clean(p["heading"]), "head", 76, DARK, lh=1.12, max_lines=2, min_size=56)
    bb = Block(d, clean(p["body"]), "body", 38, BODY_ON_CREAM, lh=1.45, max_lines=6, min_size=30)

    tip_pad = 34
    icon = 40
    tip_text_w = CONTENT_W - 2 * tip_pad - icon - 20
    tip_label = "Pro tip: "
    tb = Block(d, tip_label + clean(p["tip"]), "body", 34, GREEN_TEXT, max_w=tip_text_w,
               lh=1.4, max_lines=3, min_size=28)
    tip_h = tb.height + 2 * 30

    def draw_tip(y):
        rounded(d, [PAD_X, y, W - PAD_X, y + tip_h], 28, GREEN_BG)
        bulb_x, bulb_y = PAD_X + tip_pad, y + 32
        d.ellipse([bulb_x + 6, bulb_y, bulb_x + 34, bulb_y + 28], outline=GREEN_TEXT, width=3)
        d.line([(bulb_x + 14, bulb_y + 34), (bulb_x + 26, bulb_y + 34)], fill=GREEN_TEXT, width=3)
        d.line([(bulb_x + 16, bulb_y + 40), (bulb_x + 24, bulb_y + 40)], fill=GREEN_TEXT, width=3)
        tx = PAD_X + tip_pad + icon + 20
        # draw "Pro tip:" semibold on the first line, rest regular
        semi = font("body_semibold", tb.size)
        for i, line in enumerate(tb.lines):
            ly = y + 30 + i * tb.line_h
            if i == 0 and line.startswith("Pro tip:"):
                d.text((tx, ly), "Pro tip:", font=semi, fill=GREEN_TEXT)
                off = d.textlength("Pro tip: ", font=semi)
                d.text((tx + off, ly), line[len("Pro tip: "):], font=tb.font, fill=GREEN_TEXT)
            else:
                d.text((tx, ly), line, font=tb.font, fill=GREEN_TEXT)

    layout_center(top, bottom, [
        (num.height, lambda y: num.draw_at(PAD_X - 6, y)),
        (hb.height, lambda y: hb.draw_at(PAD_X, y)),
        (bb.height, lambda y: bb.draw_at(PAD_X, y)),
        (tip_h, draw_tip),
    ])
    return img


def render_cta(n, total):
    img, d = new_slide(True)
    top = header(img, d, n, total, True) + 40
    bottom = footer(d, n, total, True) - 40

    h1 = font("head", 84)
    rows = [("Save karo", "Next shopping se pehle ek baar dekh lena."),
            ("Share karo", "Us dost ko jo har sale mein phas jaata hai."),
            ("Daily deals chahiye?", "Telegram + WhatsApp channel — link in bio.")]
    rt, rs = font("head", 44), font("body", 32)
    row_h = 168

    def draw_title(y):
        d.text((PAD_X, y), "Ye post ", font=h1, fill=WHITE)
        x = PAD_X + d.textlength("Ye post ", font=h1)
        d.text((x, y), "kaam ki", font=h1, fill=ORANGE)
        d.text((PAD_X, y + 94), "lagi?", font=h1, fill=WHITE)

    def make_row(i, title, sub):
        def fn(y):
            rounded(d, [PAD_X, y, W - PAD_X, y + row_h], 28, (36, 37, 41))
            bx, by = PAD_X + 36, y + (row_h - 84) // 2
            rounded(d, [bx, by, bx + 84, by + 84], 22, ORANGE)
            if i == 0:
                bookmark_icon(d, bx + 20, by + 20, 44, DARK, width=4)
            elif i == 1:
                for cx, cy in [(bx + 58, by + 24), (bx + 26, by + 42), (bx + 58, by + 60)]:
                    d.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], outline=DARK, width=4)
                d.line([(bx + 33, by + 38), (bx + 51, by + 28)], fill=DARK, width=4)
                d.line([(bx + 33, by + 46), (bx + 51, by + 56)], fill=DARK, width=4)
            else:
                arrow_icon(d, bx + 20, by + 20, 44, DARK, width=5)
            tx = bx + 84 + 28
            d.text((tx, y + 36), title, font=rt, fill=WHITE)
            d.text((tx, y + 96), sub, font=rs, fill=GREY_ON_DARK)
        return fn

    items = [(188, draw_title)] + [(row_h, make_row(i, t, s)) for i, (t, s) in enumerate(rows)]
    layout_center(top, bottom, items)
    return img


def render_post(content: dict, out_dir: Path) -> list:
    """Render cover + one slide per point + CTA. Returns list of file paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    slides = content["slides"]
    total = len(slides) + 2
    imgs = [render_cover(content, 1, total)]
    for i, p in enumerate(slides, 1):
        imgs.append(render_point(p, i, i + 1, total))
    imgs.append(render_cta(total, total))
    paths = []
    for i, im in enumerate(imgs, 1):
        p = out_dir / f"slide-{i:02d}.jpg"
        im.save(p, "JPEG", quality=92, optimize=True, progressive=False)
        paths.append(p)
    return paths

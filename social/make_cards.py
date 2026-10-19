"""Genera las tarjetas 1080x1350 (4:5, lo que acepta Instagram) de social/posts.json.

Uso, desde la raíz del repo: python social/make_cards.py
Salida: social/cards/<id>.jpg. Se publican con la web, así que Instagram y Facebook
las descargan desde la URL pública. Requiere Pillow; solo se ejecuta en local.
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SOCIAL = ROOT / "social"
W, H = 1080, 1350
BG, SURFACE, TEXT, MUTED, VOLT = "#0E0F11", "#23272C", "#F2F3F5", "#A4AAB3", "#C6F135"
BLACK = str(SOCIAL / "fonts" / "Anybody-Black.ttf")
MEDIUM = str(SOCIAL / "fonts" / "Anybody-Medium.ttf")
# Marca: la H-barra de ic_brand_mark.xml (viewBox 48) como rectángulos redondeados.
MARK = [(16.08, 21.3, 31.92, 26.7, .72), (8.52, 9.6, 16.44, 38.4, 2.52), (2.76, 15.36, 7.44, 32.64, 1.98),
        (31.56, 9.6, 39.48, 38.4, 2.52), (40.56, 15.36, 45.24, 32.64, 1.98)]


def wrap(draw, text, font, width):
    lines, line = [], ""
    for word in text.split():
        probe = f"{line} {word}".strip()
        if draw.textlength(probe, font=font) <= width or not line:
            line = probe
        else:
            lines.append(line)
            line = word
    return lines + [line]


def card(post):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)

    s = 1.25
    for x1, y1, x2, y2, r in MARK:
        d.rounded_rectangle((72 + x1 * s, 64 + y1 * s, 72 + x2 * s, 64 + y2 * s), r * s, fill=VOLT)
    d.text((148, 94), "Heavy Duty Coach", font=ImageFont.truetype(MEDIUM, 34), fill=TEXT, anchor="lm")

    # El titular baja de tamaño hasta caber en 3 líneas.
    for size in (104, 92, 80, 70):
        font = ImageFont.truetype(BLACK, size)
        lines = wrap(d, post["title"], font, W - 144)
        if len(lines) <= 3:
            break
    y = 190
    for i, line in enumerate(lines):
        d.text((72, y), line, font=font, fill=VOLT if i == len(lines) - 1 else TEXT)
        y += int(size * 1.02)
    top = y + 48

    src = Image.open(ROOT / post["image"]).convert("RGB")
    if src.width < src.height:
        # Captura de la app: teléfono centrado que se sale por abajo.
        pw = 600
        shot = src.resize((pw, round(src.height * pw / src.width)), Image.LANCZOS)
        x = (W - pw) // 2
        frame = (x - 14, top, x + pw + 14, H + 60)
        d.rounded_rectangle(frame, 52, fill=SURFACE)
        mask = Image.new("L", shot.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, pw, shot.height + 60), 40, fill=255)
        im.paste(shot, (x, top + 14), mask)
    else:
        # Foto 3:2: ocupa el ancho y se recorta por arriba para llegar al borde inferior.
        h = H - top
        photo = src.resize((round(src.width * h / src.height), h), Image.LANCZOS)
        if photo.width < W:
            photo = src.resize((W, round(src.height * W / src.width)), Image.LANCZOS)
        left = (photo.width - W) // 2
        im.paste(photo.crop((left, photo.height - h, left + W, photo.height)), (0, top))
    return im


def main():
    out = SOCIAL / "cards"
    out.mkdir(exist_ok=True)
    for post in json.loads((SOCIAL / "posts.json").read_text(encoding="utf-8")):
        path = out / f"{post['id']}.jpg"
        card(post).save(path, "JPEG", quality=86, optimize=True, progressive=True)
        print(path.relative_to(ROOT), f"{path.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()

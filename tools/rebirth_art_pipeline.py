#!/usr/bin/env python3
"""Generate deterministic premium Rebirth card-art PNGs.

This is a local art pipeline helper, not production runtime code. It uses
Pillow when available and writes committed raster assets consumed by Flask.
"""

from pathlib import Path
from random import Random
import sys

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.rebirth_art import CARD_ART_PROFILES


WIDTH = 960
HEIGHT = 640


def rgba(hex_color, alpha=255):
    value = hex_color.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), alpha)


def blend(color, amount=0.25):
    r, g, b, a = color
    return (
        min(255, int(r + (255 - r) * amount)),
        min(255, int(g + (255 - g) * amount)),
        min(255, int(b + (255 - b) * amount)),
        a,
    )


def darken(color, amount=0.35):
    r, g, b, a = color
    return (int(r * (1 - amount)), int(g * (1 - amount)), int(b * (1 - amount)), a)


def make_background(profile, rng):
    accent = rgba(profile["palette"]["accent"])
    secondary = rgba(profile["palette"]["secondary"])
    shadow = rgba(profile["palette"]["shadow"])
    img = Image.new("RGBA", (WIDTH, HEIGHT), shadow)
    draw = ImageDraw.Draw(img, "RGBA")

    for y in range(HEIGHT):
        t = y / HEIGHT
        base = (
            int(shadow[0] * (1 - t) + 5 * t),
            int(shadow[1] * (1 - t) + 7 * t),
            int(shadow[2] * (1 - t) + 10 * t),
            255,
        )
        draw.line([(0, y), (WIDTH, y)], fill=base)

    glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow, "RGBA")
    for _ in range(4):
        cx = rng.randint(120, WIDTH - 120)
        cy = rng.randint(120, HEIGHT - 80)
        radius = rng.randint(160, 340)
        color = accent if rng.random() > 0.35 else secondary
        glow_draw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            fill=(color[0], color[1], color[2], rng.randint(16, 42)),
        )
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(62)))

    draw = ImageDraw.Draw(img, "RGBA")
    for x in range(-40, WIDTH + 60, 82):
        draw.line([(x, 0), (x + rng.randint(-15, 28), HEIGHT)], fill=(255, 255, 255, 10), width=1)
    for _ in range(90):
        x = rng.randint(0, WIDTH)
        y = rng.randint(0, HEIGHT)
        length = rng.randint(8, 34)
        color = accent if rng.random() > 0.5 else secondary
        draw.line(
            [(x, y), (x + rng.randint(-length, length), y + rng.randint(-length, length))],
            fill=(color[0], color[1], color[2], rng.randint(18, 58)),
            width=rng.choice([1, 1, 2]),
        )

    noise = Image.effect_noise((WIDTH, HEIGHT), 35).convert("L")
    noise_layer = Image.new("RGBA", (WIDTH, HEIGHT), (255, 255, 255, 0))
    noise_layer.putalpha(noise.point(lambda value: min(24, max(0, value - 118))))
    img.alpha_composite(noise_layer)
    return img


def add_glow(img, xy, radius, color, alpha=92):
    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    x, y = xy
    draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=(*color[:3], alpha))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(radius // 2)))


def stroke_polygon(draw, points, fill, outline, width=5):
    draw.polygon(points, fill=fill)
    closed = points + [points[0]]
    draw.line(closed, fill=outline, width=width, joint="curve")


def draw_sparks(draw, rng, color, count=80):
    for _ in range(count):
        x = rng.randint(70, WIDTH - 70)
        y = rng.randint(70, HEIGHT - 40)
        r = rng.choice([1, 1, 2, 3])
        alpha = rng.randint(50, 160)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(*color[:3], alpha))


def draw_cracks(draw, rng, color, start_points):
    for sx, sy in start_points:
        x, y = sx, sy
        for _ in range(rng.randint(2, 4)):
            nx = x + rng.randint(-38, 42)
            ny = y + rng.randint(-8, 42)
            draw.line([(x, y), (nx, ny)], fill=(*color[:3], 150), width=rng.choice([2, 3, 4]))
            x, y = nx, ny


def render_beast(img, profile, rng, *, evolved=False):
    draw = ImageDraw.Draw(img, "RGBA")
    accent = rgba(profile["palette"]["accent"])
    secondary = rgba(profile["palette"]["secondary"])
    hide = rgba("#111318")
    outline = blend(accent, 0.12)
    add_glow(img, (520, 330), 250, secondary, 84 if evolved else 58)

    body = [(210, 400), (290, 280), (470, 210), (690, 250), (795, 360), (690, 472), (470, 506), (300, 482)]
    stroke_polygon(draw, body, darken(hide, 0.1), outline, 7)
    head = [(655, 245), (790, 290), (858, 370), (780, 432), (650, 410), (606, 322)]
    stroke_polygon(draw, head, (11, 13, 15, 255), outline, 7)
    tail = [(226, 388), (104, 350), (66, 410), (206, 430)]
    stroke_polygon(draw, tail, (10, 12, 13, 245), darken(outline, 0.2), 5)
    for x in [330, 405, 490, 575, 650]:
        h = rng.randint(48, 100) + (30 if evolved else 0)
        stroke_polygon(draw, [(x - 24, 260), (x + 2, 168 - h // 4), (x + 34, 268)], (6, 8, 9, 255), outline, 5)
    for x in [330, 470, 610, 725]:
        draw.polygon([(x, 460), (x - 38, 552), (x + 22, 552)], fill=(7, 8, 9, 255))
        draw.line([(x, 460), (x - 38, 552), (x + 22, 552)], fill=outline, width=4)
    draw.polygon([(800, 372), (892, 354), (815, 404)], fill=(224, 214, 184, 230))
    draw.ellipse([760, 318, 784, 342], fill=secondary)
    draw_cracks(draw, rng, secondary, [(350, 360), (468, 306), (590, 346), (710, 378)])
    draw_sparks(draw, rng, accent, 110 if evolved else 76)


def render_guardian(img, profile, rng, *, metal=False, evolved=False):
    draw = ImageDraw.Draw(img, "RGBA")
    accent = rgba(profile["palette"]["accent"])
    secondary = rgba(profile["palette"]["secondary"])
    add_glow(img, (500, 338), 260, secondary, 42)

    fill = (20, 23, 22, 255) if not metal else (19, 20, 21, 255)
    outline = blend(accent, 0.08)
    base = [(278, 175), (682, 175), (760, 296), (704, 493), (480, 560), (254, 493), (198, 296)]
    if evolved:
        base = [(248, 125), (714, 125), (812, 288), (746, 520), (480, 594), (214, 520), (148, 288)]
    stroke_polygon(draw, base, fill, outline, 7)
    inner = [(324, 236), (636, 236), (684, 318), (642, 456), (480, 505), (318, 456), (276, 318)]
    stroke_polygon(draw, inner, darken(fill, 0.08), darken(outline, 0.06), 5)
    if metal:
        for x in [335, 430, 526, 620]:
            draw.rectangle([x, 198, x + 42, 500], fill=(33, 35, 37, 210), outline=outline, width=3)
        draw.polygon([(480, 176), (548, 302), (480, 468), (412, 302)], fill=(6, 7, 8, 225), outline=secondary)
    else:
        for x in [318, 406, 498, 586]:
            draw.line([(x, 220), (x + rng.randint(-18, 24), 492)], fill=(*accent[:3], 82), width=3)
        draw_cracks(draw, rng, secondary, [(430, 280), (540, 310), (360, 384)])
    draw_sparks(draw, rng, secondary, 54)


def render_avian(img, profile, rng, *, evolved=False):
    draw = ImageDraw.Draw(img, "RGBA")
    accent = rgba(profile["palette"]["accent"])
    secondary = rgba(profile["palette"]["secondary"])
    add_glow(img, (480, 280), 310, secondary, 70)
    outline = blend(accent, 0.05)

    left_wing = [(480, 230), (165, 134), (250, 342), (96, 448), (380, 390)]
    right_wing = [(480, 230), (795, 134), (710, 342), (864, 448), (580, 390)]
    if evolved:
        left_wing = [(480, 210), (92, 92), (208, 350), (54, 510), (392, 410)]
        right_wing = [(480, 210), (868, 92), (752, 350), (906, 510), (568, 410)]
    stroke_polygon(draw, left_wing, (15, 19, 22, 248), outline, 6)
    stroke_polygon(draw, right_wing, (15, 19, 22, 248), outline, 6)
    body = [(480, 118), (590, 370), (480, 545), (370, 370)]
    stroke_polygon(draw, body, (14, 17, 18, 255), outline, 7)
    chest = [(480, 182), (532, 336), (480, 428), (428, 336)]
    stroke_polygon(draw, chest, (32, 37, 38, 238), secondary, 4)
    for offset in [-170, -110, -55, 55, 110, 170]:
        draw.line([(480, 268), (480 + offset, 410 + abs(offset) // 2)], fill=(*secondary[:3], 118), width=4)
    draw.ellipse([466, 204, 494, 232], fill=accent)
    if evolved:
        for x in [290, 670, 438, 522]:
            draw.line([(x, 86), (x + rng.randint(-45, 45), 500)], fill=(*secondary[:3], 118), width=3)


def render_assassin(img, profile, rng, *, hunter=False):
    draw = ImageDraw.Draw(img, "RGBA")
    accent = rgba(profile["palette"]["accent"])
    secondary = rgba(profile["palette"]["secondary"])
    add_glow(img, (530, 320), 260, accent, 58)
    outline = blend(accent, 0.03)

    if hunter:
        body = [(188, 398), (310, 300), (526, 260), (742, 318), (842, 408), (696, 450), (448, 430), (260, 480)]
        head = [(668, 272), (818, 304), (890, 370), (782, 410), (650, 382)]
        stroke_polygon(draw, body, (5, 7, 11, 255), outline, 6)
        stroke_polygon(draw, head, (4, 5, 9, 255), outline, 5)
        draw.ellipse([768, 338, 790, 360], fill=secondary)
        for x in [330, 464, 602, 722]:
            draw.line([(x, 418), (x - 44, 548)], fill=outline, width=8)
    else:
        body = [(536, 86), (340, 272), (296, 418), (436, 548), (650, 318)]
        blade = [(568, 108), (398, 350), (774, 210)]
        stroke_polygon(draw, body, (8, 9, 14, 250), outline, 7)
        stroke_polygon(draw, blade, (12, 13, 18, 235), secondary, 5)
        draw.polygon([(412, 420), (676, 286), (514, 528)], fill=(28, 30, 39, 210))
        draw.ellipse([530, 226, 552, 248], fill=rgba("#65d7ff"))
    for _ in range(24):
        x = rng.randint(80, WIDTH - 80)
        y = rng.randint(80, HEIGHT - 80)
        draw.line([(x, y), (x + rng.randint(80, 190), y - rng.randint(40, 120))], fill=(*accent[:3], rng.randint(18, 58)), width=2)


def render_wyrm(img, profile, rng, *, evolved=False):
    draw = ImageDraw.Draw(img, "RGBA")
    accent = rgba(profile["palette"]["accent"])
    secondary = rgba(profile["palette"]["secondary"])
    add_glow(img, (560, 350), 330, secondary, 92)
    outline = blend(accent, 0.12)

    for width, alpha, yoff in [(110, 235, 0), (78, 255, -6), (45, 255, -12)]:
        points = [(170, 448 + yoff), (288, 310 + yoff), (432, 280 + yoff), (576, 350 + yoff), (780, 252 + yoff)]
        draw.line(points, fill=(13, 10, 8, alpha), width=width, joint="curve")
        draw.line(points, fill=outline, width=4, joint="curve")
    head = [(700, 210), (860, 260), (884, 366), (742, 416), (638, 330)]
    stroke_polygon(draw, head, (10, 8, 7, 255), outline, 7)
    wing_l = [(470, 300), (326, 138), (404, 360)]
    wing_r = [(560, 324), (720, 122), (654, 388)]
    stroke_polygon(draw, wing_l, (18, 11, 8, 210), darken(outline, 0.1), 4)
    stroke_polygon(draw, wing_r, (18, 11, 8, 210), darken(outline, 0.1), 4)
    for x in [330, 410, 496, 590, 700]:
        draw.polygon([(x, 286), (x + 24, 210 - (30 if evolved else 0)), (x + 64, 300)], fill=(5, 5, 5, 240), outline=outline)
    draw.ellipse([790, 296, 818, 324], fill=accent)
    if evolved:
        draw.polygon([(756, 214), (788, 128), (822, 218)], fill=(8, 5, 4, 245), outline=outline)
        draw.polygon([(824, 242), (876, 166), (872, 286)], fill=(8, 5, 4, 245), outline=outline)
    draw_cracks(draw, rng, secondary, [(410, 334), (540, 360), (682, 318)])
    draw_sparks(draw, rng, accent, 120)


def render_card(card_id, profile):
    rng = Random(card_id)
    img = make_background(profile, rng)

    if card_id in {"dreadmaw"}:
        render_beast(img, profile, rng, evolved=True)
    elif card_id in {"stoneshell", "stonewarden"}:
        render_guardian(img, profile, rng, metal=False, evolved=card_id == "stonewarden")
    elif card_id in {"ironbastion", "ironbulwark"}:
        render_guardian(img, profile, rng, metal=True, evolved=card_id == "ironbulwark")
    elif card_id in {"skywarden", "stormwarden"}:
        render_avian(img, profile, rng, evolved=card_id == "stormwarden")
    elif card_id == "shadewisp":
        render_assassin(img, profile, rng)
    elif card_id in {"voidstalker", "nightfang"}:
        render_assassin(img, profile, rng, hunter=True)
    elif card_id in {"embermaw", "embermaw_alpha"}:
        render_wyrm(img, profile, rng, evolved=card_id == "embermaw_alpha")
    else:
        render_beast(img, profile, rng)

    vignette = Image.new("L", (WIDTH, HEIGHT), 0)
    vd = ImageDraw.Draw(vignette)
    vd.ellipse([-180, -90, WIDTH + 180, HEIGHT + 160], fill=210)
    vignette = Image.eval(vignette.filter(ImageFilter.GaussianBlur(68)), lambda value: 255 - value)
    shade = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    shade.putalpha(vignette.point(lambda value: min(190, value)))
    img.alpha_composite(shade)
    return img.convert("RGB")


def main():
    out_dir = ROOT / "static" / "assets" / "rebirth" / "cards"
    out_dir.mkdir(parents=True, exist_ok=True)
    for card_id, profile in CARD_ART_PROFILES.items():
        if profile["status"] == "approved_reference_crop":
            continue
        out_path = ROOT / profile["path"].lstrip("/")
        image = render_card(card_id, profile)
        image.save(out_path, format="PNG", optimize=True)
        print(out_path.relative_to(ROOT))


if __name__ == "__main__":
    main()

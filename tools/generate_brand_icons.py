"""Generate story_gen brand icon assets for web and docs surfaces."""

from __future__ import annotations

import json
import math
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

INK = (31, 27, 23, 255)
PRIMARY = (46, 71, 61, 255)
PRIMARY_STRONG = (33, 53, 45, 255)
ACCENT = (164, 91, 42, 255)
ACCENT_STRONG = (126, 68, 29, 255)
PAPER = (247, 242, 230, 255)
PARCHMENT = (239, 227, 204, 255)
BORDER = (204, 185, 154, 255)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _mix_rgb(
    base: tuple[int, int, int, int], top: tuple[int, int, int, int], t: float
) -> tuple[int, int, int, int]:
    return (
        int(round(_lerp(base[0], top[0], t))),
        int(round(_lerp(base[1], top[1], t))),
        int(round(_lerp(base[2], top[2], t))),
        255,
    )


def _set_pixel(
    canvas: bytearray, size: int, x: int, y: int, color: tuple[int, int, int, int]
) -> None:
    if not (0 <= x < size and 0 <= y < size):
        return
    idx = (y * size + x) * 4
    src_a = color[3] / 255.0
    dst_r = canvas[idx]
    dst_g = canvas[idx + 1]
    dst_b = canvas[idx + 2]
    out_r = int(round(dst_r * (1 - src_a) + color[0] * src_a))
    out_g = int(round(dst_g * (1 - src_a) + color[1] * src_a))
    out_b = int(round(dst_b * (1 - src_a) + color[2] * src_a))
    canvas[idx] = out_r
    canvas[idx + 1] = out_g
    canvas[idx + 2] = out_b
    canvas[idx + 3] = 255


def _fill_rect(
    canvas: bytearray,
    size: int,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    color: tuple[int, int, int, int],
) -> None:
    left = max(0, min(x0, x1))
    right = min(size, max(x0, x1))
    top = max(0, min(y0, y1))
    bottom = min(size, max(y0, y1))
    for y in range(top, bottom):
        for x in range(left, right):
            _set_pixel(canvas, size, x, y, color)


def _fill_rounded_rect(
    canvas: bytearray,
    size: int,
    x0: int,
    y0: int,
    width: int,
    height: int,
    radius: int,
    color: tuple[int, int, int, int],
) -> None:
    if width <= 0 or height <= 0:
        return
    r = max(0, min(radius, width // 2, height // 2))
    x1 = x0 + width
    y1 = y0 + height
    _fill_rect(canvas, size, x0 + r, y0, x1 - r, y1, color)
    _fill_rect(canvas, size, x0, y0 + r, x0 + r, y1 - r, color)
    _fill_rect(canvas, size, x1 - r, y0 + r, x1, y1 - r, color)
    corners = (
        (x0 + r, y0 + r),
        (x1 - r - 1, y0 + r),
        (x0 + r, y1 - r - 1),
        (x1 - r - 1, y1 - r - 1),
    )
    for cx, cy in corners:
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                dx = x - cx
                dy = y - cy
                if dx * dx + dy * dy <= r * r:
                    _set_pixel(canvas, size, x, y, color)


def _stroke_circle(
    canvas: bytearray,
    size: int,
    cx: float,
    cy: float,
    radius: float,
    thickness: float,
    color: tuple[int, int, int, int],
) -> None:
    r_outer = radius + thickness / 2
    r_inner = max(0.0, radius - thickness / 2)
    x0 = int(max(0, math.floor(cx - r_outer - 1)))
    x1 = int(min(size - 1, math.ceil(cx + r_outer + 1)))
    y0 = int(max(0, math.floor(cy - r_outer - 1)))
    y1 = int(min(size - 1, math.ceil(cy + r_outer + 1)))
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            dx = (x + 0.5) - cx
            dy = (y + 0.5) - cy
            dist = math.sqrt(dx * dx + dy * dy)
            if r_inner <= dist <= r_outer:
                _set_pixel(canvas, size, x, y, color)


def _draw_line(
    canvas: bytearray,
    size: int,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    width: float,
    color: tuple[int, int, int, int],
) -> None:
    min_x = int(max(0, math.floor(min(x0, x1) - width - 1)))
    max_x = int(min(size - 1, math.ceil(max(x0, x1) + width + 1)))
    min_y = int(max(0, math.floor(min(y0, y1) - width - 1)))
    max_y = int(min(size - 1, math.ceil(max(y0, y1) + width + 1)))

    vx = x1 - x0
    vy = y1 - y0
    denom = vx * vx + vy * vy
    if denom == 0:
        return
    half = width / 2
    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            px = x + 0.5
            py = y + 0.5
            t = _clamp(((px - x0) * vx + (py - y0) * vy) / denom, 0.0, 1.0)
            proj_x = x0 + vx * t
            proj_y = y0 + vy * t
            dx = px - proj_x
            dy = py - proj_y
            if dx * dx + dy * dy <= half * half:
                _set_pixel(canvas, size, x, y, color)


def _fill_diamond(
    canvas: bytearray,
    size: int,
    cx: float,
    cy: float,
    radius: float,
    color: tuple[int, int, int, int],
) -> None:
    x0 = int(max(0, math.floor(cx - radius - 1)))
    x1 = int(min(size - 1, math.ceil(cx + radius + 1)))
    y0 = int(max(0, math.floor(cy - radius - 1)))
    y1 = int(min(size - 1, math.ceil(cy + radius + 1)))
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            dx = abs((x + 0.5) - cx)
            dy = abs((y + 0.5) - cy)
            if dx + dy <= radius:
                _set_pixel(canvas, size, x, y, color)


def _fill_spark(
    canvas: bytearray,
    size: int,
    cx: float,
    cy: float,
    arm: float,
    core: float,
    color: tuple[int, int, int, int],
) -> None:
    x0 = int(max(0, math.floor(cx - arm - 1)))
    x1 = int(min(size - 1, math.ceil(cx + arm + 1)))
    y0 = int(max(0, math.floor(cy - arm - 1)))
    y1 = int(min(size - 1, math.ceil(cy + arm + 1)))
    diag = arm * 0.9
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            dx = abs((x + 0.5) - cx)
            dy = abs((y + 0.5) - cy)
            horizontal = dx <= arm and dy <= core
            vertical = dy <= arm and dx <= core
            diagonal = dx + dy <= diag
            if horizontal or vertical or diagonal:
                _set_pixel(canvas, size, x, y, color)


def _render_icon(size: int) -> bytes:
    canvas = bytearray(size * size * 4)
    center = size / 2
    for y in range(size):
        for x in range(size):
            nx = (x + 0.5) / size - 0.5
            ny = (y + 0.5) / size - 0.5
            dist = min(1.0, math.sqrt(nx * nx + ny * ny) / 0.72)
            shade = _clamp(0.85 - dist * 0.65, 0.0, 1.0)
            base = _mix_rgb(INK, PRIMARY, shade)
            idx = (y * size + x) * 4
            canvas[idx] = base[0]
            canvas[idx + 1] = base[1]
            canvas[idx + 2] = base[2]
            canvas[idx + 3] = 255

    ring_color = (BORDER[0], BORDER[1], BORDER[2], 140)
    _stroke_circle(
        canvas,
        size,
        cx=center,
        cy=center * 0.94,
        radius=size * 0.325,
        thickness=size * 0.05,
        color=ring_color,
    )

    book_x = int(size * 0.22)
    book_y = int(size * 0.54)
    book_w = int(size * 0.56)
    book_h = int(size * 0.29)
    book_radius = int(size * 0.05)

    _fill_rounded_rect(
        canvas, size, book_x - 2, book_y - 2, book_w + 4, book_h + 4, book_radius, BORDER
    )
    _fill_rounded_rect(canvas, size, book_x, book_y, book_w, book_h, book_radius, PARCHMENT)
    _fill_rect(
        canvas,
        size,
        int(size * 0.497),
        int(size * 0.56),
        int(size * 0.503),
        int(size * 0.83),
        (122, 99, 72, 200),
    )
    _fill_rect(
        canvas,
        size,
        int(size * 0.26),
        int(size * 0.61),
        int(size * 0.47),
        int(size * 0.64),
        (255, 251, 242, 175),
    )
    _fill_rect(
        canvas,
        size,
        int(size * 0.53),
        int(size * 0.61),
        int(size * 0.74),
        int(size * 0.64),
        (255, 251, 242, 175),
    )

    _draw_line(
        canvas,
        size,
        x0=size * 0.32,
        y0=size * 0.42,
        x1=size * 0.67,
        y1=size * 0.24,
        width=size * 0.075,
        color=ACCENT_STRONG,
    )
    _draw_line(
        canvas,
        size,
        x0=size * 0.32,
        y0=size * 0.41,
        x1=size * 0.67,
        y1=size * 0.23,
        width=size * 0.043,
        color=ACCENT,
    )

    nib_x = size * 0.69
    nib_y = size * 0.23
    _fill_diamond(canvas, size, nib_x, nib_y, size * 0.047, PRIMARY_STRONG)
    _fill_diamond(canvas, size, nib_x, nib_y, size * 0.037, PAPER)
    _fill_diamond(canvas, size, nib_x + size * 0.012, nib_y, size * 0.01, PRIMARY_STRONG)

    _fill_spark(
        canvas,
        size,
        cx=size * 0.77,
        cy=size * 0.165,
        arm=size * 0.05,
        core=size * 0.013,
        color=PAPER,
    )
    _fill_spark(
        canvas,
        size,
        cx=size * 0.77,
        cy=size * 0.165,
        arm=size * 0.035,
        core=size * 0.01,
        color=ACCENT,
    )

    return _encode_png(size, size, bytes(canvas))


def _png_chunk(tag: bytes, payload: bytes) -> bytes:
    crc = zlib.crc32(tag + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", crc)


def _encode_png(width: int, height: int, rgba: bytes) -> bytes:
    raw = bytearray()
    stride = width * 4
    for y in range(height):
        raw.append(0)
        start = y * stride
        raw.extend(rgba[start : start + stride])
    compressed = zlib.compress(bytes(raw), level=9)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", compressed)
        + _png_chunk(b"IEND", b"")
    )


def _encode_ico(entries: list[tuple[int, bytes]]) -> bytes:
    count = len(entries)
    header = struct.pack("<HHH", 0, 1, count)
    directory = bytearray()
    offset = 6 + 16 * count
    payload = bytearray()
    for size, png_bytes in entries:
        width_byte = 0 if size >= 256 else size
        height_byte = 0 if size >= 256 else size
        directory.extend(
            struct.pack(
                "<BBBBHHII",
                width_byte,
                height_byte,
                0,
                0,
                1,
                32,
                len(png_bytes),
                offset,
            )
        )
        payload.extend(png_bytes)
        offset += len(png_bytes)
    return header + bytes(directory) + bytes(payload)


def _brand_svg() -> str:
    return """<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 512 512\" role=\"img\" aria-label=\"story_gen brand mark\">
  <defs>
    <radialGradient id=\"sg-bg\" cx=\"36%\" cy=\"34%\" r=\"75%\">
      <stop offset=\"0%\" stop-color=\"#2E473D\"/>
      <stop offset=\"100%\" stop-color=\"#1F1B17\"/>
    </radialGradient>
  </defs>
  <rect x=\"0\" y=\"0\" width=\"512\" height=\"512\" rx=\"112\" fill=\"url(#sg-bg)\"/>
  <circle cx=\"256\" cy=\"241\" r=\"166\" fill=\"none\" stroke=\"#CCB99A\" stroke-width=\"24\" stroke-opacity=\"0.55\"/>
  <rect x=\"113\" y=\"276\" width=\"286\" height=\"148\" rx=\"28\" fill=\"#CCB99A\"/>
  <rect x=\"121\" y=\"284\" width=\"270\" height=\"132\" rx=\"24\" fill=\"#EFE3CC\"/>
  <line x1=\"256\" y1=\"292\" x2=\"256\" y2=\"416\" stroke=\"#7A6348\" stroke-width=\"6\" stroke-opacity=\"0.8\"/>
  <rect x=\"136\" y=\"312\" width=\"104\" height=\"12\" fill=\"#FFF8EE\" fill-opacity=\"0.72\"/>
  <rect x=\"272\" y=\"312\" width=\"104\" height=\"12\" fill=\"#FFF8EE\" fill-opacity=\"0.72\"/>
  <line x1=\"164\" y1=\"212\" x2=\"344\" y2=\"122\" stroke=\"#7E441D\" stroke-width=\"38\" stroke-linecap=\"round\"/>
  <line x1=\"164\" y1=\"212\" x2=\"344\" y2=\"122\" stroke=\"#A45B2A\" stroke-width=\"22\" stroke-linecap=\"round\"/>
  <polygon points=\"353,98 377,122 353,146 329,122\" fill=\"#21352D\"/>
  <polygon points=\"353,106 369,122 353,138 337,122\" fill=\"#F7F2E6\"/>
  <polygon points=\"359,122 365,128 359,134 353,128\" fill=\"#21352D\"/>
  <path d=\"M394 57l8 23h23l-18 14 7 23-20-13-20 13 7-23-18-14h23z\" fill=\"#F7F2E6\"/>
  <path d=\"M394 67l5 15h15l-12 9 5 15-13-9-13 9 5-15-12-9h15z\" fill=\"#A45B2A\"/>
</svg>
"""


def _safari_svg() -> str:
    return """<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 512 512\">
  <rect x=\"120\" y=\"284\" width=\"272\" height=\"132\" rx=\"24\" fill=\"#000\"/>
  <rect x=\"252\" y=\"292\" width=\"8\" height=\"124\" fill=\"#fff\"/>
  <path d=\"M164 212l180-90\" stroke=\"#000\" stroke-width=\"38\" stroke-linecap=\"round\"/>
  <path d=\"M394 57l8 23h23l-18 14 7 23-20-13-20 13 7-23-18-14h23z\" fill=\"#000\"/>
</svg>
"""


def _manifest_payload() -> dict[str, object]:
    return {
        "name": "story_gen studio",
        "short_name": "story_gen",
        "description": "Story engineering studio with deterministic analysis and dashboards.",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#1F1B17",
        "theme_color": "#2E473D",
        "icons": [
            {
                "src": "icons/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": "icons/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": "icons/icon-512-maskable.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable",
            },
        ],
    }


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def main() -> None:
    web_public = ROOT / "web" / "public"
    docs_brand = ROOT / "docs" / "assets" / "brand"

    brand_svg = _brand_svg()
    safari_svg = _safari_svg()

    _write(web_public / "favicon.svg", brand_svg)
    _write(web_public / "safari-pinned-tab.svg", safari_svg)
    _write(web_public / "brand" / "story-gen-mark.svg", brand_svg)
    _write(docs_brand / "story-gen-mark.svg", brand_svg)
    _write(docs_brand / "story-gen-favicon.svg", brand_svg)

    icon_16 = _render_icon(16)
    icon_32 = _render_icon(32)
    icon_180 = _render_icon(180)
    icon_192 = _render_icon(192)
    icon_512 = _render_icon(512)

    _write_bytes(web_public / "icons" / "icon-16.png", icon_16)
    _write_bytes(web_public / "icons" / "icon-32.png", icon_32)
    _write_bytes(web_public / "icons" / "apple-touch-icon.png", icon_180)
    _write_bytes(web_public / "icons" / "icon-192.png", icon_192)
    _write_bytes(web_public / "icons" / "icon-512.png", icon_512)
    _write_bytes(web_public / "icons" / "icon-512-maskable.png", icon_512)
    _write_bytes(web_public / "favicon.ico", _encode_ico([(16, icon_16), (32, icon_32)]))

    manifest = json.dumps(_manifest_payload(), indent=2) + "\n"
    _write(web_public / "site.webmanifest", manifest)

    print("Generated brand icons for web and docs.")


if __name__ == "__main__":
    main()

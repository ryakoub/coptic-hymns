#!/usr/bin/env python3
"""Draws the Coptic Chanter logo and every image made from it, into brand/.

The seal: Ⲓⲏ̅ⲥ̅ Ⲡⲭ̅ⲥ̅ over a faint gold Coptic cross in the inner circle; COPTIC CHANTER over the top of the
ring, PRAISE HIM under it, Ⲁ on the left and Ⲱ on the right in red. All lettering is drawn as shapes (the
Coptic from Arial Coptic, the English from Cinzel SemiBold), so the files need no fonts.

    python3 tools/logo/build_logo.py <ArialCoptic.ttf>      (needs fontTools; PNGs need `cairosvg` on the PATH)

Writes brand/logo.svg (the seal), brand/logo-mono.svg (one colour, for watermarks), brand/mark.svg (the
inner circle alone, for icons) and the PNGs the app and the website use.
"""
import math
import subprocess
import sys
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parent
OUT = HERE.parent.parent / 'brand'

TEAL, GOLD, RED, GROUND, CROSS = '#0E6F8F', '#C9A13B', '#8E1B1B', '#FBF4E2', '#D9A82E'
CROSS_OPACITY = 0.22


class Font:
    def __init__(self, path):
        self.font = TTFont(path)
        self.glyphs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        self.upm = self.font['head'].unitsPerEm

    def glyph(self, ch):
        name = self.cmap[ord(ch)]
        pen, box = SVGPathPen(self.glyphs), BoundsPen(self.glyphs)
        self.glyphs[name].draw(pen)
        self.glyphs[name].draw(box)
        return pen.getCommands(), self.glyphs[name].width, box.bounds


def on_arc(font, text, radius, size, spacing, offset, top):
    """Text along a circle round (200,200), as SVGs textPath would set it: over the top (left to right,
    letters standing outward) or under the bottom (left to right, letters standing inward)."""
    k = size / font.upm
    widths = [font.glyph(ch)[1] * k + spacing if ch != ' ' else font.glyphs[font.cmap[32]].width * k + spacing
              for ch in text]
    s = math.pi * radius * offset - sum(widths) / 2
    out = []
    for ch, w in zip(text, widths):
        if ch != ' ':
            d, adv, _ = font.glyph(ch)
            mid = s + adv * k / 2
            phi = math.pi - mid / radius if top else math.pi + mid / radius
            x, y = 200 + radius * math.cos(phi), 200 - radius * math.sin(phi)
            turn = 90 - math.degrees(phi) if top else 270 - math.degrees(phi)
            out.append(f'<path transform="translate({x:.2f},{y:.2f}) rotate({turn:.2f}) scale({k:.5f},{-k:.5f}) '
                       f'translate({-adv / 2:.1f},0)" d="{d}"/>')
        s += w
    return ''.join(out)


def coptic_line(font, word, over):
    """Letters at their advances, with a titlo over the letters at the indices in `over`."""
    x, parts, spans = 0, [], []
    for ch in word:
        d, adv, (x0, _, x1, _) = font.glyph(ch)
        parts.append(f'<path transform="translate({x},0)" d="{d}"/>')
        spans.append((x + x0, x + x1))
        x += adv
    a, b = spans[over[0]][0] + 40, spans[over[-1]][1] - 40
    parts.append(f'<rect x="{a}" y="1250" width="{b - a}" height="96" rx="48"/>')
    lows = [font.glyph(ch)[2][1] for ch in word]
    highs = [font.glyph(ch)[2][3] for ch in word] + [1346]
    return ''.join(parts), spans[0][0], spans[-1][1], min(lows), max(highs)


def monogram(font, color, size=150, gap=420):
    """Ⲓⲏ̅ⲥ̅ above Ⲡⲭ̅ⲥ̅, centred at (200,200), fitted in a size × size square."""
    lines = [coptic_line(font, 'Ⲓⲏⲥ', [1, 2]), coptic_line(font, 'Ⲡⲭⲥ', [1, 2])]
    total = sum(hi - lo for *_, lo, hi in lines) + gap
    s = min(size / max(x1 - x0 for _, x0, x1, _, _ in lines), size / total)
    out, top = [], total / 2
    for paths, x0, x1, lo, hi in lines:
        out.append(f'<g transform="translate({-(x0 + x1) / 2},{top - hi})">{paths}</g>')
        top -= (hi - lo) + gap
    return f'<g fill="{color}" transform="translate(200,200) scale({s:.5f},{-s:.5f})">{"".join(out)}</g>'


def letter(font, ch, color, cx, cy, height):
    d, _, (x0, y0, x1, y1) = font.glyph(ch)
    s = height / (y1 - y0)
    return (f'<g fill="{color}" transform="translate({cx},{cy}) scale({s:.5f},{-s:.5f}) '
            f'translate({-(x0 + x1) / 2},{-(y0 + y1) / 2})"><path d="{d}"/></g>')


def cross(color, opacity):
    """A budded Coptic cross: the longer arm below, three lobes at each end."""
    lobes = []
    for x, y, dx, dy in [(200, 104, 0, 1), (200, 302, 0, -1), (131, 171, 1, 0), (269, 171, -1, 0)]:
        bx, by = x + dx * 12, y + dy * 12
        lobes += [f'<circle cx="{x}" cy="{y}" r="12"/>',
                  f'<circle cx="{bx + 12 if dy else bx}" cy="{by if dy else by - 12}" r="11"/>',
                  f'<circle cx="{bx - 12 if dy else bx}" cy="{by if dy else by + 12}" r="11"/>']
    return (f'<g fill="{color}" opacity="{opacity}" transform="translate(200,200) scale(0.85) translate(-200,-200)">'
            '<rect x="189" y="112" width="22" height="182"/><rect x="139" y="160" width="122" height="22"/>'
            + ''.join(lobes) + '</g>')


def svg(body, view='0 0 400 400', label='Coptic Chanter'):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view}" role="img" aria-label="{label}">'
            f'<title>{label}</title>{body}</svg>\n')


def seal(coptic, latin, mono=None):
    """The whole seal; `mono` draws it all in one colour, without the grounds (for a watermark)."""
    teal, gold, red, ground, inner = (mono,) * 3 + ('none', 'none') if mono else (TEAL, GOLD, RED, GROUND, '#FFFFFF')
    return (f'<circle cx="200" cy="200" r="192" fill="{ground}" stroke="{gold}" stroke-width="2"/>'
            f'<circle cx="200" cy="200" r="182" fill="none" stroke="{teal}" stroke-width="3"/>'
            f'<circle cx="200" cy="200" r="108" fill="{inner}" stroke="{gold}" stroke-width="4"/>'
            + cross(mono or CROSS, 0.35 if mono else CROSS_OPACITY)
            + f'<g fill="{teal}">' + on_arc(latin, 'COPTIC CHANTER', 142, 31, 5, 0.5, True)
            + on_arc(latin, 'PRAISE HIM', 168, 26, 17, 0.516, False) + '</g>'
            + letter(coptic, 'Ⲁ', red, 43, 200, 28) + letter(coptic, 'Ⲱ', red, 357, 200, 28)
            + monogram(coptic, teal))


def mark(coptic, ground=GROUND):
    """The inner circle alone on a square ground: the app icon and the favicon."""
    return (f'<rect width="400" height="400" fill="{ground}"/>'
            f'<g transform="translate(200,200) scale(1.62) translate(-200,-200)">'
            f'<circle cx="200" cy="200" r="108" fill="#FFFFFF" stroke="{GOLD}" stroke-width="4"/>'
            f'<circle cx="200" cy="200" r="114" fill="none" stroke="{TEAL}" stroke-width="2.5"/>'
            + cross(CROSS, CROSS_OPACITY) + monogram(coptic, TEAL, size=136) + '</g>')


def png(src, dst, width, height=None, background=None):
    args = ['cairosvg', str(src), '-o', str(dst), '--output-width', str(width), '--output-height', str(height or width)]
    if background:
        args += ['-b', background]
    subprocess.run(args, check=True)


def main():
    coptic = Font(sys.argv[1])
    latin = Font(HERE / 'fonts' / 'Cinzel-SemiBold.ttf')
    OUT.mkdir(exist_ok=True)
    (OUT / 'logo.svg').write_text(svg(seal(coptic, latin)))
    (OUT / 'logo-mono.svg').write_text(svg(seal(coptic, latin, mono='#000000')))
    (OUT / 'mark.svg').write_text(svg(mark(coptic)))
    # The sharing picture: the seal on the app's teal, 1200 × 630.
    (OUT / 'social.svg').write_text(svg(
        f'<rect width="1200" height="630" fill="#075276"/><g transform="translate(345,40) scale(1.375)">'
        + seal(coptic, latin) + '</g>', view='0 0 1200 630'))
    png(OUT / 'mark.svg', OUT / 'icon-1024.png', 1024)
    png(OUT / 'mark.svg', OUT / 'apple-touch-icon.png', 180)
    png(OUT / 'logo.svg', OUT / 'logo-1032.png', 1032)
    png(OUT / 'social.svg', OUT / 'social.png', 1200, 630)
    print('wrote', ', '.join(sorted(p.name for p in OUT.iterdir())))


if __name__ == '__main__':
    main()

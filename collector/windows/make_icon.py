"""Draws the collector icon (teal tile with a pulse line, like frontend/public/logo.svg)."""
import sys
from PIL import Image, ImageDraw

def tile(size):
    s = size / 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=14 * s, fill=(8, 127, 140, 255))
    pts = [(6, 40), (17, 40), (22, 29), (30, 50), (36, 35), (40, 40), (58, 40)]
    d.line([(x * s, y * s) for x, y in pts], fill='white', width=max(2, round(4.5 * s)), joint='curve')
    r = 3 * s
    d.ellipse([44 * s - r, 24 * s - r, 44 * s + r, 24 * s + r], fill=(189, 242, 234, 255))
    return img

tile(256).save(sys.argv[1], sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

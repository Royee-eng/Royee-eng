#!/usr/bin/env python3
"""Build original, dependency-light profile diagrams; Pillow is used only for the GIF.

Nothing here modifies the AI-generated photographic hero.
Run: python scripts/build_art.py
"""
from pathlib import Path
import math
from html import escape

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
BG = "#0c1717"
PANEL = "#112220"
MUTED = "#52665f"
ACCENT = "#abc0b6"
FG = "#e7edeb"
FONT = "Arial, Helvetica, sans-serif"


def svg(w, h, title, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">'
            f'<title>{escape(title)}</title><rect width="{w}" height="{h}" rx="16" fill="{BG}"/>'
            f'<g font-family="{FONT}">{body}</g></svg>\n')


def text(x, y, value, size=28, color=FG, weight=400, spacing=0):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" '
            f'font-weight="{weight}" letter-spacing="{spacing}">{escape(value)}</text>')


def relief(cx, cy, radius, count, stretch=1.0):
    paths = []
    for n in range(count):
        r = radius + n * 16
        pts = []
        for i in range(121):
            a = i / 120 * math.tau
            bump = 1 + .1 * math.sin(3 * a + n * .04) + .06 * math.sin(7 * a)
            pts.append((cx + math.cos(a) * r * bump * stretch,
                        cy + math.sin(a) * r * bump))
        paths.append(pts)
    return paths


def polyline(points, color, width=1, opacity=1, dashed=False):
    coords = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    dash = ' stroke-dasharray="5 9"' if dashed else ''
    return f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="{width}" opacity="{opacity}" stroke-linecap="round"{dash}/>'


def smooth(points, steps=22):
    # Catmull-Rom sampling gives SVG and GIF exactly the same route geometry.
    pp = [points[0], *points, points[-1]]
    result = []
    for i in range(1, len(pp)-2):
        a,b,c,d = pp[i-1:i+3]
        for j in range(steps):
            t=j/steps
            result.append(tuple(.5*((2*b[k])+(-a[k]+c[k])*t+
                (2*a[k]-5*b[k]+4*c[k]-d[k])*t*t+
                (-a[k]+3*b[k]-3*c[k]+d[k])*t*t*t) for k in (0,1)))
    result.append(points[-1])
    return result


def write(name, data):
    (ASSETS / name).write_text(data, encoding="utf-8")


def build_about():
    body = ''.join(polyline(p, MUTED, 1, .3) for p in relief(1000, 115, 18, 25, 1.35))
    body += text(48, 51, "01 / FIELD NOTES", 19, ACCENT, 400, 3)
    body += text(45, 138, "About me", 70, FG, 600, -2)
    body += text(49, 191, "STILL LEARNING. ALWAYS EXPLORING.", 18, ACCENT, 400, 2)
    write("about.svg", svg(1200, 230, "About me — Still learning. Always exploring. Subtle topographic contour artwork.", body))


ROUTE = smooth([(66,302),(160,248),(275,218),(362,120),(480,125),(580,167),
                (680,156),(775,76),(895,110),(1020,85),(1140,35)])
CONTOURS = relief(780,190,35,14,1.65)
LABELS = [(64,58,"NOW · LEARNING","Java backend"),
          (465,270,"NEXT · EXPLORING","AI applications"),
          (867,242,"DIRECTION · AGENT SYSTEMS","Coding agents")]
NODES = [(160,248),(580,167),(1020,85)]


def build_trail():
    body = ''.join(polyline(p, MUTED, 1, .20) for p in CONTOURS)
    body += polyline(ROUTE, MUTED, 2, 1, True)
    body += polyline(ROUTE[:30], ACCENT, 3)
    for i, (x,y) in enumerate(NODES):
        body += f'<circle cx="{x}" cy="{y}" r="18" fill="{BG}" stroke="{ACCENT if i==0 else MUTED}" stroke-width="2"/>'
        body += text(x-9, y+5, f"0{i+1}", 13, FG if i==0 else ACCENT, 600)
    for x,y,caption,title in LABELS:
        body += text(x,y,caption,15,ACCENT,400,1.7)
        body += text(x,y+39,title,31,FG,600,-.4)
    body += '<circle cx="106" cy="279" r="5" fill="#e7edeb"/>'
    write("trail.svg",svg(1200,350,"Development trail: Java backend, now learning; AI applications, next exploring; Coding agents, direction Agent Systems. Dotted future route is aspirational.",body))


def build_mobile():
    contours = relief(420,300,20,18,1.2)
    body = ''.join(polyline(p,MUTED,1,.22) for p in contours)
    route = smooth([(60,55),(95,110),(54,190),(95,280),(60,370),(95,465),(60,553)])
    body += polyline(route,MUTED,2,1,True) + polyline(route[:30],ACCENT,3)
    labels = [(110,"NOW · LEARNING","Java backend"),
              (280,"NEXT · EXPLORING","AI applications"),
              (465,"DIRECTION","Coding agents")]
    for i,(y,caption,title) in enumerate(labels):
        body += f'<circle cx="95" cy="{y}" r="20" fill="{BG}" stroke="{ACCENT if i==0 else MUTED}" stroke-width="2"/>'
        body += text(85,y+6,f"0{i+1}",15,FG if i==0 else ACCENT,600)
        body += text(143,y-13,caption,16,ACCENT,400,1.2)
        body += text(142,y+28,title,34,FG,600,-.5)
        if i == 2:
            body += text(144,y+60,"Agent Systems",21,ACCENT)
    write("trail-mobile.svg",svg(540,600,"Development trail: Java backend, now learning; AI applications, next exploring; Coding agents, direction Agent Systems.",body))


def build_badges():
    for name,label,status,width in [("java","Java","learning",190),("python","Python","learning",208),("agents","Agent systems","exploring",275)]:
        split = 24 + len(label)*8
        body = f'<rect x="{split}" width="{width-split}" height="36" fill="{PANEL}"/>'
        body += text(13,24,label,15,FG,600)
        body += text(split+13,24,status,14,ACCENT)
        write(f"badge-{name}.svg",svg(width,36,f"{label}: {status}",body))


def build_beyond():
    body = ''.join(polyline(p,MUTED,1,.16) for p in relief(1120,110,15,12,1.8))
    for x in (400,800):
        body += f'<path d="M{x} 42V138" stroke="{MUTED}" opacity=".45"/>'
    # Original line icons: mountain route, motion, camera.
    body += f'<g fill="none" stroke="{ACCENT}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round">'
    body += '<path d="M55 105L82 60L96 81L110 67L137 105ZM72 77L82 85L92 76M96 105L106 94L99 89"/>'
    body += '<circle cx="488" cy="65" r="7"/><path d="M485 77L472 93L487 103L478 122M485 77L501 88L515 82M485 77L470 75L457 87M472 93L456 112L443 112"/>'
    body += '<path d="M850 76H866L872 66H894L900 76H918V115H850ZM855 71H863"/><circle cx="884" cy="96" r="13"/>'
    body += '</g>'
    for x,title,sub in [(166,"Hiking","Find a new trail."),(545,"Sport","Keep moving."),(947,"Photography","Notice more.")]:
        body += text(x,85,title,29,FG,600,-.5) + text(x,116,sub,17,ACCENT)
    write("beyond.svg",svg(1200,180,"Beyond code: hiking, sport, and photography.",body))


def build_gif():
    from PIL import Image, ImageDraw, ImageFont
    def font(size, bold=False):
        candidates = [f"/System/Library/Fonts/Supplemental/Arial{' Bold' if bold else ''}.ttf",
                      f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf"]
        for path in candidates:
            if Path(path).exists(): return ImageFont.truetype(path,size)
        return ImageFont.load_default(size=size)
    base=Image.new("RGB",(1200,350),BG)
    d=ImageDraw.Draw(base)
    for points in CONTOURS: d.line(points,fill="#1a2724",width=1)
    for i in range(0,len(ROUTE)-1,3): d.line(ROUTE[i:i+2],fill=MUTED,width=2)
    d.line(ROUTE[:30],fill=ACCENT,width=3)
    for i,(x,y) in enumerate(NODES):
        d.ellipse((x-18,y-18,x+18,y+18),fill=BG,outline=ACCENT if i==0 else MUTED,width=2)
        d.text((x,y),f"0{i+1}",font=font(13,True),fill=FG if i==0 else ACCENT,anchor="mm")
    for x,y,caption,title in LABELS:
        d.text((x,y),caption,font=font(15),fill=ACCENT,anchor="ls",spacing=2)
        d.text((x,y+39),title,font=font(31,True),fill=FG,anchor="ls")
    frames=[]
    # Restrict movement to the short current-learning segment. Never animate future milestones.
    for i in range(40):
        frame=base.copy(); draw=ImageDraw.Draw(frame)
        k=4+round((1-math.cos(math.tau*i/40))/2*13)
        x,y=ROUTE[k]
        draw.ellipse((x-9,y-9,x+9,y+9),outline=MUTED,width=1)
        draw.ellipse((x-4,y-4,x+4,y+4),fill=FG)
        frames.append(frame)
    frames[0].save(ASSETS/"trail.gif",save_all=True,append_images=frames[1:],
                   duration=150,loop=0,optimize=True,disposal=1)


if __name__ == "__main__":
    ASSETS.mkdir(parents=True,exist_ok=True)
    build_about(); build_trail(); build_mobile(); build_badges(); build_beyond(); build_gif()
    print("Built about, desktop/mobile trail, badges, beyond-code SVGs and 6-second trail GIF.")

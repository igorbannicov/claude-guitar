"""Калькулятор гитарного мастера: лады, натяжение, подбор калибров, угол грифа, SVG-шаблон.

python guitar.py frets 25.5 [--frets 24] [--bass 27 --perp 8] [--nut-width 43 --width-12 52] [--radius 10-16]
python guitar.py tension 25.5 "E4 B3 G3 D3 A2 E2" "10 13 17 26w 36w 46w"
python guitar.py gauges 25.5 "D4 A3 F3 C3 G2 C2" --target 16  |  --match "10 13 17 26w 36w 46w"
python guitar.py neck 24.75 --saddle 19 --board-height 6 --joint-fret 16
python guitar.py svg 25.5 [--bass 27 --perp 8] [--a4] -o fretboard.svg
python guitar.py chord Abm7+9 [--count 4] [--tuning "D4 A3 F3 C3 G2 C2"]
Мензура: дюймы (25.5) или миллиметры (648mm).
"""
import argparse
import itertools
import math
import re

# D'Addario String Tension Specifications (tension_chart_13934.pdf), lb/in.
# PL — plain steel, NW — XL nickelplated steel round wound.
PLAIN = {
    .007: .00001085, .008: .00001418, .0085: .00001601, .009: .00001794,
    .0095: .00001999, .010: .00002215, .0105: .00002442, .011: .00002680,
    .0115: .00002930, .012: .00003190, .013: .00003744, .0135: .00004037,
    .014: .00004342, .015: .00004984, .016: .00005671, .017: .00006402,
    .018: .00007177, .019: .00007997, .020: .00008861, .022: .00010722,
    .024: .00012760, .026: .00014975,
}
WOUND = {
    .017: .00005524, .018: .00006215, .019: .00006947, .020: .00007495,
    .021: .00008293, .022: .00009184, .024: .00010857, .026: .00012671,
    .028: .00014666, .030: .00017236, .032: .00019347, .034: .00021590,
    .036: .00023964, .038: .00026471, .039: .00027932, .042: .00032279,
    .044: .00035182, .046: .00038216, .048: .00041382, .049: .00043014,
    .052: .00048109, .054: .00053838, .056: .00057598, .059: .00064191,
    .060: .00066542, .062: .00070697, .064: .00074984, .066: .00079889,
    .068: .00084614, .070: .00089304, .072: .00094124, .074: .00098869,
    .080: .00115011,
}
G = 386.4  # in/s², ускорение свободного падения
MM = 25.4
LB_KG = 0.45359237
NOTES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
STANDARD = "E4 B3 G3 D3 A2 E2 B1 F#1".split()
INLAYS = (3, 5, 7, 9, 12, 15, 17, 19, 21, 24)


def scale_in(s):
    s = s.lower().strip()
    return float(s[:-2]) / MM if s.endswith("mm") else float(s)


def fret_x(L, n):
    """Расстояние от порожка до лада n, 12-TET."""
    return L - L / 2 ** (n / 12)


def note_midi(note):
    m = re.fullmatch(r"([A-Ga-g])([#b]?)(-?\d)", note)
    if not m:
        raise SystemExit(f"Не понял ноту: {note} (пример: E4, C#3, Bb1)")
    semi = NOTES[m[1].upper()] + {"#": 1, "b": -1, "": 0}[m[2]]
    return 12 * (int(m[3]) + 1) + semi


def note_hz(note):
    return 440 * 2 ** ((note_midi(note) - 69) / 12)


def parse_gauge(g):
    m = re.fullmatch(r"(0?\.\d+|\d+(?:\.\d+)?)([pw]?)", g.lower())
    if not m:
        raise SystemExit(f"Не понял калибр: {g} (пример: 10, .010, 26w, 17p)")
    d = float(m[1]) if "." in m[1] and float(m[1]) < 1 else float(m[1]) / 1000
    wound = m[2] == "w" or (m[2] == "" and d > .020)
    return d, wound


def unit_weight(d, wound):
    """Вес погонного дюйма: из таблицы или интерполяция log-log по соседям."""
    table = WOUND if wound else PLAIN
    if d in table:
        return table[d], True
    keys = sorted(table)
    lo = max([k for k in keys if k < d], default=keys[0])
    hi = min([k for k in keys if k > d], default=keys[-1])
    if lo == hi:  # за краем таблицы: два крайних значения
        lo, hi = (keys[0], keys[1]) if d < keys[0] else (keys[-2], keys[-1])
    p = math.log(table[hi] / table[lo]) / math.log(hi / lo)
    return table[lo] * (d / lo) ** p, False


def string_tension(L, note, d, wound):
    uw, exact = unit_weight(d, wound)
    return uw * (2 * L * note_hz(note)) ** 2 / G, exact


def frets(args):
    Lt = scale_in(args.scale)
    Lb = scale_in(args.bass) if args.bass else Lt
    multi = Lb != Lt
    head = f"Мензура {Lt:.3f}\" = {Lt * MM:.1f} мм"
    if multi:
        head += f", басы {Lb:.3f}\" = {Lb * MM:.1f} мм, перпендикулярный лад {args.perp}"
    print(head + ", 12-TET")
    cols = ["лад", "дисканты, мм" if multi else "от порожка, мм"]
    cols += ["басы, мм"] if multi else ["от пред., мм", "дюйм"]
    widths = args.nut_width is not None and args.width_12 is not None
    radius = [float(r) for r in args.radius.split("-")] if args.radius else None
    if widths:
        cols.append("ширина, мм")
    if radius:
        cols.append("радиус, дюйм")
    print("  ".join(f"{c:>14}" for c in cols))
    L = (Lt + Lb) / 2  # ширина и радиус — по средней линии
    last = fret_x(L, args.frets)
    for n in range(1, args.frets + 1):
        x = fret_x(L, n)
        row = [f"{n:>14}", f"{fret_x(Lt, n) * MM:>14.2f}"]
        if multi:
            row.append(f"{fret_x(Lb, n) * MM:>14.2f}")
        else:
            row += [f"{(x - fret_x(L, n - 1)) * MM:>14.2f}", f"{x:>14.4f}"]
        if widths:
            row.append(f"{args.nut_width + (args.width_12 - args.nut_width) * x / fret_x(L, 12):>14.2f}")
        if radius:
            r = radius[0] + (radius[-1] - radius[0]) * x / last
            row.append(f"{r:>14.2f}")
        print("  ".join(row))
    if multi:
        print("Расстояния — от порожка вдоль крайней струны своей стороны.")


def check_order(notes):
    if note_hz(notes[0]) < note_hz(notes[-1]):
        raise SystemExit("Ноты перечисляются от 1-й (тонкой) струны к басовой — похоже, порядок перевёрнут")


def report(L, notes, specs):
    print(f"Мензура {L:.3f}\" = {L * MM:.1f} мм")
    print(f"{'#':>2}  {'нота':>4}  {'Гц':>7}  {'калибр':>8}  {'lb':>6}  {'кг':>6}")
    total, approx = 0, False
    for i, (n, (d, wound)) in enumerate(zip(notes, specs), 1):
        t, exact = string_tension(L, n, d, wound)
        total += t
        approx |= not exact
        mark = "" if exact else "≈"
        print(f"{i:>2}  {n:>4}  {note_hz(n):>7.2f}  {d:.4f}{'w' if wound else 'p'}  {mark}{t:>5.1f}  {t * LB_KG:>6.2f}")
    if any(not 8 <= string_tension(L, n, d, w)[0] <= 30 for n, (d, w) in zip(notes, specs)):
        print("Внимание: натяжение вне 8–30 lb — струна будет болтаться или рискует порваться")
    print(f"Всего: {total:.1f} lb = {total * LB_KG:.1f} кг")
    if approx:
        print("≈ — калибра нет в таблице D'Addario, вес интерполирован")


def tension(args):
    notes, gauges = args.tuning.split(), args.gauges.split()
    if len(notes) != len(gauges):
        raise SystemExit(f"Нот {len(notes)}, калибров {len(gauges)} — должно совпадать")
    check_order(notes)
    report(scale_in(args.scale), notes, [parse_gauge(g) for g in gauges])


def gauges(args):
    L, notes = scale_in(args.scale), args.tuning.split()
    check_order(notes)
    if args.match:
        ref = [parse_gauge(g) for g in args.match.split()]
        ref_notes = args.match_tuning.split() if args.match_tuning else STANDARD[:len(ref)]
        if len(ref) != len(notes) or len(ref_notes) != len(notes):
            raise SystemExit("В --match и --match-tuning столько же струн, сколько нот в строе")
        targets = [string_tension(L, n, d, w)[0] for n, (d, w) in zip(ref_notes, ref)]
        print(f"Цель — натяжение {args.match} в {' '.join(ref_notes)} на той же мензуре")
    elif args.target:
        targets = [float(t) for t in args.target.split(",")]
        targets = targets * len(notes) if len(targets) == 1 else targets
        if len(targets) != len(notes):
            raise SystemExit("--target: одно число или по числу на каждую струну через запятую")
        print(f"Цель — {', '.join(f'{t:g}' for t in targets)} lb")
    else:
        raise SystemExit("Нужен --target или --match")
    specs = []
    for i, (n, t) in enumerate(zip(notes, targets), 1):
        wound = i >= args.wound_from
        table = WOUND if wound else PLAIN
        d = min(table, key=lambda k: abs(string_tension(L, n, k, wound)[0] - t))
        specs.append((d, wound))
    report(L, notes, specs)
    print("Комплект:", " ".join(f"{round(d * 1000, 1):g}{'w' if w else ''}" for d, w in specs))


def neck(args):
    L = scale_in(args.scale) * MM
    d = L - fret_x(L, args.joint_fret)
    # струна идёт от порожка (≈ высота лада над накладкой) с подъёмом action на 12-м ладу
    string_at_saddle = args.fret + 2 * args.action
    rise = args.saddle - args.board_height - string_at_saddle
    angle = math.degrees(math.atan(rise / d))
    print(f"Мензура {L:.1f} мм, корпус начинается у {args.joint_fret}-го лада, до седла {d:.1f} мм")
    print(f"Угол грифа: {angle:.2f}° ({'назад' if angle > 0 else 'вперёд' if angle < 0 else 'без наклона'})")
    print(f"Neck projection (линейка по ладам у седла над декой): {args.saddle - 2 * args.action:.1f} мм")
    print(f"Струна у седла над плоскостью накладки: {string_at_saddle:.1f} мм")


def svg(args):
    Lt = scale_in(args.scale) * MM
    Lb = (scale_in(args.bass) if args.bass else scale_in(args.scale)) * MM
    perp = args.perp if args.bass else 0
    w0, w12, N = args.nut_width, args.width_12, args.frets
    sn = w0 - 2 * args.edge  # разнос крайних струн у порожка
    sb = args.bridge_spread
    ot, ob = -fret_x(Lt, perp), -fret_x(Lb, perp)
    shift = -min(ot, ob)
    ot, ob = ot + shift, ob + shift  # x порожка у дискантов и у басов

    def point(n, side):  # side -1 — дисканты (сверху), +1 — басы
        o, L = (ot, Lt) if side < 0 else (ob, Lb)
        x = o + fret_x(L, n)
        return x, side * (sn / 2 + (sb - sn) / 2 * (x - o) / L)

    xc0 = (point(0, -1)[0] + point(0, 1)[0]) / 2
    xc12 = (point(12, -1)[0] + point(12, 1)[0]) / 2

    def edge(x):  # полуширина накладки
        return w0 / 2 + (w12 - w0) / 2 * (x - xc0) / (xc12 - xc0)

    def line(n, extra=0.0):  # линия лада, продлённая до краёв накладки
        (xt, yt), (xb, yb) = point(n, -1), point(n, 1)
        xt, xb = xt + extra, xb + extra
        k = (xb - xt) / (yb - yt)
        a, b = w0 / 2 - (w12 - w0) / 2 * xc0 / (xc12 - xc0), (w12 - w0) / 2 / (xc12 - xc0)
        ends = []
        for s in (-1, 1):  # y = s * (a + b x), x = xt + (y - yt) k
            y = s * (a + b * (xt - yt * k)) / (1 - s * b * k)
            ends.append((xt + (y - yt) * k, y))
        return ends

    def mid(n):  # центр между ладами n-1 и n на средней линии
        return sum(line(m)[0][0] + line(m)[1][0] for m in (n - 1, n)) / 4

    end = line(N, args.tail)
    nut = line(0)
    xmax, ymax = max(p[0] for p in end), edge(max(p[0] for p in end))
    els = [f'<polygon points="{" ".join(f"{x:.3f},{y:.3f}" for x, y in nut + end[::-1])}" class="b"/>',
           f'<line x1="-5" y1="0" x2="{xmax + 5:.3f}" y2="0" class="c"/>']
    for n in range(N + 1):
        (x1, y1), (x2, y2) = line(n)
        els.append(f'<line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}" class="{"n" if n == 0 else "f"}"/>')
        if n:
            xm = mid(n)
            els.append(f'<text x="{xm:.2f}" y="{edge(xm) + 6:.2f}" class="t">{n}</text>')
    for n in (i for i in INLAYS if i <= N):
        xm = mid(n)
        ys = (-edge(xm) / 2, edge(xm) / 2) if n % 12 == 0 else (0,)
        els += [f'<circle cx="{xm:.2f}" cy="{y:.2f}" r="3" class="d"/>' for y in ys]
    title = f"Мензура {Lt:.1f} мм" + (f" / {Lb:.1f} мм, перпендикулярный лад {perp}" if Lb != Lt else "")
    title += f" · {N} ладов · порожек {w0:g} мм, 12-й лад {w12:g} мм"
    ry = ymax + 14
    ruler = [f'<line x1="0" y1="{ry}" x2="100" y2="{ry}" class="f"/>']
    ruler += [f'<line x1="{i}" y1="{ry - (3 if i % 50 else 5)}" x2="{i}" y2="{ry}" class="f"/>' for i in range(0, 101, 10)]
    ruler.append(f'<text x="50" y="{ry + 5}" class="t">100 мм — проверь масштаб печати</text>')
    style = ("<style>.b{fill:none;stroke:#000;stroke-width:.3}.f{stroke:#000;stroke-width:.2}"
             ".n{stroke:#000;stroke-width:.8}.c{stroke:#888;stroke-width:.15;stroke-dasharray:3 2}"
             ".d{fill:none;stroke:#000;stroke-width:.2}.t{font:3.5px sans-serif;text-anchor:middle}"
             ".g{stroke:#c00;stroke-width:.2;stroke-dasharray:2 1}</style>")

    def doc(x0, y0, w, h, body):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.1f}mm" height="{h:.1f}mm" '
                f'viewBox="{x0:.3f} {y0:.3f} {w:.3f} {h:.3f}">{style}'
                f'<rect x="{x0:.3f}" y="{y0:.3f}" width="{w:.3f}" height="{h:.3f}" fill="#fff"/>{body}</svg>\n')

    def write(path, text):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(path)

    if not args.a4:
        h = 2 * ymax + 50
        body = f'<text x="0" y="{-ymax - 12:.2f}" class="t" style="text-anchor:start">{title}</text>'
        write(args.out, doc(-10, -ymax - 20, xmax + 20, h, body + "".join(els + ruler)))
        return
    # A4 альбом: 277 мм полезной длины, листы перекрываются на 10 мм
    step, pages = 267, []
    x0 = -10
    while not pages or x0 + 277 < xmax + 10:
        pages.append(x0)
        x0 += step
    base = args.out[:-4] if args.out.endswith(".svg") else args.out
    for i, x0 in enumerate(pages, 1):
        glue = [x for x in (x0, x0 + step) if (x != x0 or i > 1) and (x == x0 or i < len(pages))]
        marks = "".join(f'<line x1="{x}" y1="-95" x2="{x}" y2="95" class="g"/>'
                        f'<text x="{x}" y="99" class="t">склейка ✂</text>' for x in glue)
        body = f'<text x="{x0 + 5}" y="-95" class="t" style="text-anchor:start">{title} · лист {i}/{len(pages)}</text>'
        write(f"{base}-{i}.svg", doc(x0 - 10, -105, 297, 210, body + "".join(els + (ruler if i == 1 else [])) + marks))
    print("Печатать в масштабе 100% (без «подогнать по размеру»), склеить по красным линиям.")


NOTES_BY_PC = "C C# D Eb E F F# G Ab A Bb B".split()
DEGREE = {2: 2, 4: 5, 6: 9, 7: 10, 9: 2, 11: 5, 13: 9}
NATURAL = {"3": 4, "5": 7, "7": 11, "6": 9, "9": 2, "11": 5, "13": 9, "2": 2, "4": 5}


def pitch_class(name):
    return (NOTES[name[0]] + {"#": 1, "b": -1}.get(name[1:], 0)) % 12


def parse_chord(sym):
    """Аккорд -> (тоника, бас, {ступень: полутоны от тоники}, необязательные ступени)."""
    m = re.fullmatch(r"([A-G][#b]?)(.*?)(?:/([A-G][#b]?))?", sym.strip())
    if not m:
        raise SystemExit(f"Не понял аккорд: {sym} (пример: Am, C7, Abm7+9, F#m7b5, G/B)")
    root, rest, bass = m[1], m[2], m[3] or m[1]
    t = {"1": 0, "3": 4, "5": 7}
    optional = set()

    def take(pattern):
        nonlocal rest
        mm = re.match(pattern, rest)
        if mm:
            rest = rest[mm.end():]
        return mm

    n = None
    if mm := take(r"(?:maj|ma|M|Δ)(7|9|11|13)?"):
        t["7"], n = 11, mm[1] or "7"
    elif take(r"ø7?"):
        t.update({"3": 3, "5": 6, "7": 10})
    elif take(r"(?:dim|°|o)7"):
        t.update({"3": 3, "5": 6, "7": 9})
    elif take(r"dim|°|o"):
        t.update({"3": 3, "5": 6})
    elif take(r"aug|\+(?!\d)"):
        t["5"] = 8
    elif take(r"min|m(?!aj)|-(?!\d)"):
        t["3"] = 3
        if mm := take(r"(?:maj|ma|M|Δ)(7|9|11|13)?"):
            t["7"], n = 11, mm[1] or "7"
    if n is None and (mm := take(r"6/9|69|13|11|9|7|6|5")):
        n = mm[0]
    if n == "5":
        del t["3"]
    elif n in ("6", "6/9", "69"):
        t["6"] = 9
        if n != "6":
            t["9"] = 2
    elif n:
        t.setdefault("7", 10)
        if int(n) >= 9:
            t["9"] = 2
        if n == "11":
            t["11"] = 5
        if n == "13":
            t["13"] = 9
        if int(n) >= 11:
            optional.add("9")
    while rest:
        if take(r"[(),\s]"):
            continue
        if mm := take(r"sus([24]?)"):
            t.pop("3", None)
            d = mm[1] or "4"
            t[d] = DEGREE[int(d)]
        elif mm := take(r"(?:add|\+)(\d+)"):
            d = int(mm[1])
            if d == 5:
                t["5"] = 8
            elif d in DEGREE:
                t[str(d)] = DEGREE[d]
            else:
                raise SystemExit(f"Не понял ступень {d} в аккорде {sym}")
        elif mm := take(r"(#|b|-)(5|9|11|13)"):
            d = mm[2]
            t[d] = NATURAL[d] + (1 if mm[1] == "#" else -1)
        elif mm := take(r"(?:no|omit)(\d)"):
            t.pop(mm[1], None)
        else:
            raise SystemExit(f"Не понял часть «{rest}» в аккорде {sym}")
    if t.get("5") == 7 and len(t) >= 4:
        optional.add("5")
    return root, bass, t, optional


def interval_label(degree, semi):
    if degree == "1":
        return "1"
    if degree == "7" and semi == 9:
        return "bb7"
    return {-1: "b", 1: "#", 0: ""}[(semi - NATURAL[degree] + 6) % 12 - 6] + degree


def spell(root, degree, semi):
    """Имя ноты по ступени: буква отсчитывается от тоники (Abm -> Ab Cb Eb)."""
    letters = "CDEFGAB"
    letter = letters[(letters.index(root[0]) + int(degree) - 1) % 7]
    diff = (pitch_class(root) + semi - NOTES[letter] + 6) % 12 - 6
    if abs(diff) == 2:  # дубль-диез/бемоль упрощаем: E7#9 -> G, а не F##
        return NOTES_BY_PC[(pitch_class(root) + semi) % 12]
    return letter + {-1: "b", 0: "", 1: "#"}[diff]


def barre(v):
    """(лад, сколько струн под пальцем, первая, последняя) или None."""
    fretted = [f for f in v if f]
    if not fretted:
        return None
    low = min(fretted)
    at = [i for i, f in enumerate(v) if f == low]
    if len(at) < 2 or {0, None} & set(v[at[0]:at[-1] + 1]):
        return None
    return low, len(at), at[0], at[-1]


def diagram_frame(v):
    """Первый показанный лад и число ладов в диаграмме."""
    fretted = [f for f in v if f]
    start = 1 if not fretted or max(fretted) <= 4 else min(fretted)
    return start, max(4, max(fretted, default=0) - start + 1)


def text_diagrams(vs):
    """Диаграммы аккорда псевдографикой: струны слева направо от басовой."""
    blocks = []
    for v in vs:
        v = v[::-1]
        start, rows = diagram_frame(v)
        lines = [" ".join("x" if f is None else "o" if f == 0 else " " for f in v) + "   ",
                 ("═" if start == 1 else "─") * (2 * len(v) - 1) + "   "]
        for r in range(start, start + rows):
            lines.append(" ".join("●" if f == r else "│" for f in v) + (f" {start:<2}" if r == start and start > 1 else "   "))
        blocks.append(lines)
    for row in zip(*[b + [" " * len(b[0])] * (max(map(len, blocks)) - len(b)) for b in blocks]):
        print("   " + "   ".join(row))


def svg_diagrams(name, vs, path):
    """Диаграммы аккорда картинкой, как в аккордниках."""
    sx, fy, x0, y0, cell = 14, 18, 22, 34, 110
    els = []
    for k, v in enumerate(vs):
        v = v[::-1]
        n = len(v)
        ox = k * cell
        start, rows = diagram_frame(v)
        right = ox + x0 + sx * (n - 1)
        for i in range(n):
            x = ox + x0 + sx * i
            els.append(f'<line x1="{x}" y1="{y0}" x2="{x}" y2="{y0 + fy * rows}" class="l"/>')
            f = v[i]
            if f is None:
                els.append(f'<path d="M{x - 4},{y0 - 14}l8,8m0,-8l-8,8" class="l"/>')
            elif f == 0:
                els.append(f'<circle cx="{x}" cy="{y0 - 10}" r="4" class="o"/>')
        for r in range(rows + 1):
            y = y0 + fy * r
            els.append(f'<line x1="{ox + x0}" y1="{y}" x2="{right}" y2="{y}" class="{"n" if r == 0 and start == 1 else "l"}"/>')
        if start > 1:
            els.append(f'<text x="{ox + x0 - 6}" y="{y0 + fy * 0.5 + 4}" class="t" style="text-anchor:end">{start}fr</text>')
        b = barre(v)
        if b:
            fb, _, i1, i2 = b
            y = y0 + fy * (fb - start + 0.5)
            els.append(f'<rect x="{ox + x0 + sx * i1 - 5}" y="{y - 5}" width="{sx * (i2 - i1) + 10}" height="10" rx="5" class="d"/>')
        for i, f in enumerate(v):
            if f and not (b and f == b[0]):
                els.append(f'<circle cx="{ox + x0 + sx * i}" cy="{y0 + fy * (f - start + 0.5)}" r="5" class="d"/>')
        els.append(f'<text x="{(ox + x0 + right) / 2}" y="{y0 + fy * rows + 20}" class="t b">{name}</text>')
    h = y0 + fy * 4 + 30
    style = ("<style>.l{stroke:#000;stroke-width:1;fill:none}.n{stroke:#000;stroke-width:4}"
             ".o{fill:none;stroke:#000;stroke-width:1.3}.d{fill:#4a5bd0}"
             ".t{font:12px sans-serif;text-anchor:middle}.b{font-weight:bold;font-size:15px}</style>")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{cell * len(vs)}" height="{h}" '
                 f'viewBox="0 0 {cell * len(vs)} {h}">{style}<rect width="100%" height="100%" fill="#fff"/>'
                 f'{"".join(els)}</svg>\n')
    print(path)


def voicings(open_midi, root_pc, bass_pc, tones, optional, max_fret=15, span=4):
    """Перебор аппликатур в окне span ладов (+ открытые струны); лучшая на каждую позицию."""
    pcs = {(root_pc + v) % 12 for v in tones.values()}
    required = {(root_pc + v) % 12 for d, v in tones.items() if d not in optional}
    best = {}
    for pos in range(0, max_fret - span + 2):
        window = [0] + list(range(max(pos, 1), pos + span))
        opts = [[None] + [f for f in window if (o + f) % 12 in pcs] for o in open_midi]
        for v in itertools.product(*opts):
            sound = [(o + f, i) for i, (o, f) in enumerate(zip(open_midi, v)) if f is not None]
            if len(sound) < min(len(open_midi), max(3, len(required))):
                continue
            got = {m % 12 for m, _ in sound}
            if not required <= got or min(sound)[0] % 12 != bass_pc:
                continue
            fretted = [f for f in v if f]
            low = min(fretted, default=0)
            if fretted and max(fretted) - low >= span:
                continue
            fingers = len(fretted)
            if b := barre(v):
                fingers -= b[1] - 1
            if fingers > 4 or (0 in v and max(fretted, default=0) > 5):  # открытые — только у порожка
                continue
            idx = [i for _, i in sound]
            gaps = sum(1 for i in range(min(idx), max(idx)) if v[i] is None)
            score = (len(sound) - 1.5 * gaps - 0.5 * (len(open_midi) - len(sound)) + v.count(0) - 0.5 * fingers
                     - 0.4 * low - 0.75 * (max(fretted, default=0) - low) + 0.5 * len(got))
            key = "open" if 0 in v else low  # из открытых — только лучшая
            if score > best.get(key, (-99, None))[0]:
                best[key] = (score, v)
    return [v for _, v in sorted(best.values(), key=lambda sv: -sv[0])]


def chord(args):
    tuning = args.tuning.split() if args.tuning else STANDARD[:6]
    open_midi = [note_midi(n) for n in tuning]
    root, bass, tones, optional = parse_chord(args.chord)
    rpc, bpc = pitch_class(root), pitch_class(bass)
    order = sorted(tones.items(), key=lambda dv: int(dv[0]))
    print(f"{args.chord}: " + "  ".join(
        f"{spell(root, d, v)}({interval_label(d, v)}{'?' if d in optional else ''})" for d, v in order))
    vs = voicings(open_midi, rpc, bpc, tones, optional)[:args.count]
    if not vs:
        raise SystemExit("Удобной аппликатуры в 4 ладах не нашлось")
    compact = ["-".join("x" if f is None else str(f) for f in reversed(v)) for v in vs]
    w = max(8, max(map(len, compact)) + 2)
    print("   " + "".join(f"{'откр.' if 0 in v else min(f for f in v if f)!s:^{w}}" for v in vs))
    for i, n in enumerate(tuning):
        lab = n[:-1].upper() if i == len(tuning) - 1 else n[:-1].lower()
        print(f"{lab:>2}|" + "".join(f"{'x' if v[i] is None else v[i]!s:-^{w - 1}}|" for v in vs))
    print("   " + "".join(f"{c:^{w}}" for c in compact))
    print("Сверху — позиция (нижний лад), снизу — запись от басовой струны." + (" ? — ступень можно опустить." if optional else ""))
    print()
    text_diagrams(vs)
    if args.svg:
        svg_diagrams(args.chord, vs, args.svg)


p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
sub = p.add_subparsers(required=True)

f = sub.add_parser("frets", help="положение ладов")
f.add_argument("scale")
f.add_argument("--frets", type=int, default=24)
f.add_argument("--bass", help="мензура басовой стороны (мультимензура)")
f.add_argument("--perp", type=int, default=0, help="перпендикулярный лад (мультимензура)")
f.add_argument("--nut-width", type=float, help="ширина накладки у порожка, мм")
f.add_argument("--width-12", type=float, help="ширина накладки у 12-го лада, мм")
f.add_argument("--radius", help="радиус, дюймы: 9.5 или compound 10-16")
f.set_defaults(fn=frets)

t = sub.add_parser("tension", help="натяжение струн")
t.add_argument("scale")
t.add_argument("tuning", help='ноты от 1-й струны: "E4 B3 G3 D3 A2 E2"')
t.add_argument("gauges", help='калибры: "10 13 17 26w 36w 46w" (p — гладкая, w — навивка)')
t.set_defaults(fn=tension)

g = sub.add_parser("gauges", help="подбор калибров под строй")
g.add_argument("scale")
g.add_argument("tuning", help='ноты от 1-й струны: "D4 A3 F3 C3 G2 C2"')
g.add_argument("--target", help="натяжение, lb: 16 или по струнам 15,15,16,17,18,18")
g.add_argument("--match", help='как у этого комплекта: "10 13 17 26w 36w 46w"')
g.add_argument("--match-tuning", help="строй эталона (по умолчанию стандартный E)")
g.add_argument("--wound-from", type=int, default=4, help="с какой струны навивка (по умолчанию 4)")
g.set_defaults(fn=gauges)

k = sub.add_parser("neck", help="угол грифа к корпусу")
k.add_argument("scale")
k.add_argument("--saddle", type=float, required=True, help="верх седла над декой, мм")
k.add_argument("--board-height", type=float, required=True, help="верх накладки над декой у стыка, мм")
k.add_argument("--joint-fret", type=int, required=True, help="лад, у которого начинается корпус")
k.add_argument("--fret", type=float, default=1.2, help="высота лада, мм")
k.add_argument("--action", type=float, default=1.6, help="зазор над 12-м ладом, мм")
k.set_defaults(fn=neck)

s = sub.add_parser("svg", help="шаблон накладки 1:1")
s.add_argument("scale")
s.add_argument("--bass", help="мензура басовой стороны (мультимензура)")
s.add_argument("--perp", type=int, default=8, help="перпендикулярный лад (мультимензура)")
s.add_argument("--frets", type=int, default=24)
s.add_argument("--nut-width", type=float, default=43)
s.add_argument("--width-12", type=float, default=52)
s.add_argument("--edge", type=float, default=3.5, help="от крайней струны до края у порожка, мм")
s.add_argument("--bridge-spread", type=float, default=52, help="разнос крайних струн на бридже, мм")
s.add_argument("--tail", type=float, default=6, help="накладка за последним ладом, мм")
s.add_argument("--a4", action="store_true", help="разбить на листы A4 для склейки")
s.add_argument("-o", "--out", default="fretboard.svg")
s.set_defaults(fn=svg)

c = sub.add_parser("chord", help="аппликатуры аккорда")
c.add_argument("chord", help="Am, C7, Abm7+9, F#m7b5, Cmaj9, G/B, Dsus4, E7#9")
c.add_argument("--count", type=int, default=4, help="сколько вариантов показать")
c.add_argument("--tuning", help="строй от 1-й струны (по умолчанию E-standard)")
c.add_argument("--svg", help="сохранить диаграммы картинкой в этот .svg")
c.set_defaults(fn=chord)

a = p.parse_args()
a.fn(a)

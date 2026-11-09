"""Geometria mínima para verificar primitivos do E3D numericamente.

Datums (Iron Rules IR-1, verificadas no E3D 3.1):
  CYLI / CONE / BOX / PYRA -> POS = centro geométrico
  DISH                    -> POS = plano do aro (tangente); cresce HEIG em +Z local
  EXTR                    -> POS = plano da extremidade do perfil; cresce HEIG em +Z local
Eixo de revolução = Z local (IR-3).
"""
from __future__ import annotations

import math
import re

DIRS = {"E": (1, 0, 0), "W": (-1, 0, 0), "N": (0, 1, 0), "S": (0, -1, 0), "U": (0, 0, 1), "D": (0, 0, -1),
        "X": (1, 0, 0), "-X": (-1, 0, 0), "Y": (0, 1, 0), "-Y": (0, -1, 0), "Z": (0, 0, 1), "-Z": (0, 0, -1)}
_NUM = r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?"


def _num(s: str) -> float:
    m = re.match(rf"\s*({_NUM})\s*(mm|m|in|ft)?", s)
    if not m:
        raise ValueError(f"número inválido: {s!r}")
    v = float(m.group(1))
    unit = (m.group(2) or "mm").lower()
    return v * {"mm": 1, "m": 1000, "in": 25.4, "ft": 304.8}[unit]


def parse_position(text: str) -> tuple[float, float, float]:
    """'E 1000mm N 2000mm U 3000mm' / 'W 5 S 3 D 1' / 'X 1 Y 2 Z 3' -> (E, N, U)."""
    t = text.upper().replace("WRT", " WRT ").split(" WRT ")[0]
    p = [0.0, 0.0, 0.0]
    for axis, val in re.findall(rf"\b([ENUWSDXYZ])\s*({_NUM}\s*(?:MM|M|IN|FT)?)", t):
        v = _num(val.lower())
        i, sign = {"E": (0, 1), "W": (0, -1), "X": (0, 1), "N": (1, 1), "S": (1, -1), "Y": (1, 1),
                   "U": (2, 1), "D": (2, -1), "Z": (2, 1)}[axis]
        p[i] = sign * v
    return tuple(p)


def _dir(text: str):
    """'N', '-X', 'E 30 N' (E girado 30° para N), 'E 45 U'."""
    t = text.strip().upper()
    m = re.match(rf"^(-?[ENUWSDXYZ])\s+({_NUM})\s+(-?[ENUWSDXYZ])$", t)
    if m:
        a, ang, b = DIRS[m.group(1)], math.radians(float(m.group(2))), DIRS[m.group(3)]
        v = tuple(math.cos(ang) * a[i] + math.sin(ang) * b[i] for i in range(3))
    else:
        v = DIRS[t]
    n = math.sqrt(sum(c * c for c in v))
    return tuple(c / n for c in v)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def parse_orientation(text: str | None):
    """'Y IS N AND Z IS U' -> eixos locais (X, Y, Z) em coordenadas do mundo."""
    if not text:
        return (1, 0, 0), (0, 1, 0), (0, 0, 1)
    t = text.upper().split(" WRT ")[0]
    axes = {}
    for part in re.split(r"\bAND\b", t):
        m = re.match(r"\s*([XYZ])\s+IS\s+(.+?)\s*$", part)
        if m:
            axes[m.group(1)] = _dir(m.group(2))
    x, y, z = axes.get("X"), axes.get("Y"), axes.get("Z")
    if z and y and not x:
        x = _cross(y, z)
    elif z and x and not y:
        y = _cross(z, x)
    elif x and y and not z:
        z = _cross(x, y)
    elif z and not x and not y:
        ref = (0, 0, 1) if abs(z[2]) < 0.9 else (0, 1, 0)
        x = _cross(ref, z)
        n = math.sqrt(sum(c * c for c in x)); x = tuple(c / n for c in x)
        y = _cross(z, x)
    if not (x and y and z):
        raise ValueError(f"orientação não suportada: {text!r}")
    return x, y, z


def extent(etype: str, pos, ori, a: dict) -> dict:
    """Caixa envolvente no mundo: {'E':(min,max),'N':(...),'U':(...)}."""
    t = etype.upper()[:4]
    x, y, z = ori
    g = lambda k, d=0.0: float(a.get(k, d) or 0.0)
    half = [0.0, 0.0, 0.0]
    c = list(pos)
    if t in ("CYLI", "CONE", "DISH", "SNOU"):
        h = g("HEIG")
        r = max(g("DIAM"), g("DTOP"), g("DBOT")) / 2
        if t == "DISH":
            c = [pos[i] + z[i] * h / 2 for i in range(3)]
        for k in range(3):
            half[k] = abs(z[k]) * h / 2 + r * math.sqrt(max(0.0, 1 - z[k] ** 2))
    elif t == "BOX":
        L = (g("XLEN"), g("YLEN"), g("ZLEN"))
        for k in range(3):
            half[k] = sum(abs(ax[k]) * L[i] / 2 for i, ax in enumerate((x, y, z)))
    elif t == "PYRA":
        L = (max(g("XBOT"), g("XTOP")), max(g("YBOT"), g("YTOP")), g("HEIG"))
        for k in range(3):
            half[k] = sum(abs(ax[k]) * L[i] / 2 for i, ax in enumerate((x, y, z)))
    elif t == "EXTR":
        h = g("HEIG")
        c = [pos[i] + z[i] * h / 2 for i in range(3)]
        for k in range(3):
            half[k] = abs(z[k]) * h / 2
    else:
        raise ValueError(f"tipo sem regra de extensão: {etype}")
    return {ax: (round(c[k] - half[k], 3), round(c[k] + half[k], 3)) for k, ax in enumerate("ENU")}

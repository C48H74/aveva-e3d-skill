"""Ponte E3D SIMULADA — mesma API HTTP do add-in E3DLiveBridge, sem E3D.

Serve para testar o loop (lint -> run -> readback -> verify -> undo) offline.
Interpreta um subconjunto de PML1: NEW / END / OLD / atributos / POS / ORI.
NÃO substitui o teste no E3D real.
"""
from __future__ import annotations

import base64
import copy
import fnmatch
import json
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    from . import geometry
except ImportError:  # pragma: no cover
    import geometry  # type: ignore

CONTAINERS = {"WORL", "SITE", "ZONE", "EQUI", "SUBE", "PIPE", "BRAN", "STRU", "FRMW"}
KNOWN = CONTAINERS | {"CYLI", "BOX", "DISH", "CONE", "PYRA", "NOZZ", "ELBO", "TEE", "VALV", "FLAN", "GASK", "REDU", "EXTR", "SCTN"}
ALIASES = {"CYLINDER": "CYLI", "PYRAMID": "PYRA", "NOZZLE": "NOZZ", "ELBOW": "ELBO", "VALVE": "VALV", "FLANGE": "FLAN",
           "GASKET": "GASK", "REDUCER": "REDU", "BRANCH": "BRAN", "EQUIPMENT": "EQUI", "STRUCTURE": "STRU", "EXTRUSION": "EXTR"}
_TINY_PNG = base64.b64encode(bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082")).decode()


class MockDB:
    def __init__(self):
        self.lock = threading.RLock()
        self.els = {}
        self.ce = "/*"
        self.undo = []
        self.dirty = False
        self.saved = 0
        self._seq = 0
        self._add("/*", "WORL", None)
        self._add("/SITE-TEST", "SITE", "/*")
        self._add("/ZONE-TEST", "ZONE", "/SITE-TEST")
        self.ce = "/ZONE-TEST"

    def _add(self, name, typ, owner, **attrs):
        self.els[name] = {"type": typ, "owner": owner, "attrs": dict(attrs), "members": []}
        if owner:
            self.els[owner]["members"].append(name)

    def resolve(self, name):
        if name.upper() == "CE":
            return self.ce
        if name not in self.els:
            raise KeyError(f"(2,109) Undefined name {name}")
        return name

    def world(self, name):
        p = [0.0, 0.0, 0.0]
        n = name
        while n:
            e = self.els[n]
            pos = e["attrs"].get("POS")
            if pos:
                q = geometry.parse_position(pos)
                p = [p[i] + q[i] for i in range(3)]
            n = e["owner"]
        return f"E {p[0]:g}mm N {p[1]:g}mm U {p[2]:g}mm"

    # ---------------- PML1 subset
    def execute(self, macro: str):
        created, modified = [], set()
        for ln, raw in enumerate(macro.splitlines(), 1):
            line = raw.split("--")[0].strip()
            if not line:
                continue
            up = line.upper()
            try:
                if up.startswith(("!", "$")):
                    raise ValueError("(41,8) comando PML2 não suportado neste contexto")
                if up.startswith("NEW "):
                    parts = line.split()
                    typ = ALIASES.get(parts[1].upper(), parts[1].upper()[:4])
                    if typ not in KNOWN:
                        raise ValueError(f"(2,109) Undefined element type {parts[1]}")
                    owner = self.ce if self.els[self.ce]["type"] in CONTAINERS else self.els[self.ce]["owner"]
                    if len(parts) > 2:
                        name = parts[2]
                        if name in self.els:
                            raise ValueError(f"(2,26) Name {name} already exists")
                    else:
                        self._seq += 1
                        name = f"={self._seq}/{typ}"
                    self._add(name, typ, owner)
                    self.ce = name
                    created.append(name)
                elif up == "END" or up.startswith("END "):
                    self.ce = self.els[self.ce]["owner"] or "/*"
                elif up.startswith("OLD "):
                    self.ce = self.resolve(line.split()[1])
                elif up.startswith("NAME "):
                    self._rename(self.ce, line.split()[1], created)
                elif up.startswith(("SAVEWORK", "DELETE", "DEL ")):
                    raise ValueError("comando bloqueado pela ponte")
                else:
                    key, _, val = line.partition(" ")
                    key = key.upper()
                    key = {"POSITION": "POS", "ORIENTATION": "ORI"}.get(key, key)
                    if key == "POS":
                        geometry.parse_position(val)
                    if key == "ORI":
                        geometry.parse_orientation(val)
                    self.els[self.ce]["attrs"][key] = val.strip()
                    if self.ce not in created:
                        modified.add(self.ce)
            except (ValueError, KeyError) as e:
                raise RuntimeError(f"Linha {ln}: {e} -> '{raw.strip()}'")
        return created, sorted(modified)

    def _rename(self, old, new, created):
        if new in self.els:
            raise ValueError(f"(2,26) Name {new} already exists")
        e = self.els.pop(old)
        self.els[new] = e
        if e["owner"]:
            m = self.els[e["owner"]]["members"]; m[m.index(old)] = new
        for c in e["members"]:
            self.els[c]["owner"] = new
        if old in created:
            created[created.index(old)] = new
        self.ce = new

    def snapshot(self):
        return copy.deepcopy((self.els, self.ce, self._seq))

    def restore(self, snap):
        self.els, self.ce, self._seq = copy.deepcopy(snap)

    def below(self, scope):
        out, stack = [], list(self.els[scope]["members"])
        while stack:
            n = stack.pop(0)
            out.append(n)
            stack[0:0] = self.els[n]["members"]
        return out

    def describe(self, name, attrs):
        e = self.els[name]
        want = [a.upper() for a in attrs] or ["NAME", "TYPE", "OWNER", "POS", "ORI", "DESC"]
        values = {}
        for a in want:
            if a == "NAME": values[a] = name
            elif a == "TYPE": values[a] = e["type"]
            elif a == "OWNER": values[a] = e["owner"]
            elif a in e["attrs"]: values[a] = e["attrs"][a]
        return {"ok": True, "name": name, "type": e["type"], "owner": e["owner"], "attributes": values,
                "world": {"pos": self.world(name), "ori": e["attrs"].get("ORI")}}


DB = MockDB()
TOKEN = "mock-token"


def handle(ep: str, p: dict) -> dict:
    db = DB
    with db.lock:
        if ep == "health":
            return {"ok": True, "project": "MOCK", "mdb": "/ALL", "user": "SYSTEM", "module": "MODEL",
                    "ce": db.ce, "pending_changes": db.dirty, "bridge": "mock"}
        if ep == "element":
            return db.describe(db.resolve(p["name"]), p.get("attributes") or [])
        if ep == "members":
            def tree(n, d):
                node = {"name": n, "type": db.els[n]["type"]}
                kids = [m for m in db.els[n]["members"]]
                if d > 0:
                    node["members"] = [tree(m, d - 1) for m in kids if not p.get("type") or db.els[m]["type"] == p["type"][:4].upper()]
                return node
            return {"ok": True, "tree": tree(db.resolve(p["name"]), p.get("depth", 1))}
        if ep == "collect":
            types = {ALIASES.get(t.upper(), t.upper()[:4]) for t in p.get("types") or []}
            rows = [db.describe(n, p.get("attributes") or ["NAME", "TYPE"])["attributes"]
                    for n in db.below(db.resolve(p["scope"])) if not types or db.els[n]["type"] in types]
            lim = p.get("limit", 500)
            return {"ok": True, "count": len(rows), "elements": rows[:lim], "truncated": len(rows) > lim}
        if ep == "find":
            names = db.below(db.resolve(p["scope"])) if p.get("scope") else list(db.els)
            hits = [{"name": n, "type": db.els[n]["type"]} for n in names
                    if fnmatch.fnmatch(n.upper(), p["pattern"].upper()) and (not p.get("type") or db.els[n]["type"] == p["type"][:4].upper())]
            return {"ok": True, "count": len(hits), "elements": hits[: p.get("limit", 200)]}
        if ep == "connections":
            n = db.resolve(p["name"])
            e = db.els[n]
            items = [{"name": m, "type": db.els[m]["type"], "cref": db.els[m]["attrs"].get("CREF")}
                     for m in db.below(n) if db.els[m]["type"] in ("NOZZ", "BRAN")]
            return {"ok": True, "element": n, "type": e["type"], "items": items,
                    "href": e["attrs"].get("HREF"), "tref": e["attrs"].get("TREF")}
        if ep == "evaluate":
            n = db.resolve(p["name"])
            if p["expression"].upper().startswith("POS WRT"):
                return {"ok": True, "value": db.world(n)}
            return {"ok": True, "value": db.els[n]["attrs"].get(p["expression"].upper())}
        if ep == "run":
            scope = db.resolve(p["scope"])
            snap = db.snapshot()
            db.ce = scope
            try:
                created, modified = db.execute(p["macro"])
            except RuntimeError as e:
                db.restore(snap)
                return {"ok": False, "error": str(e), "rolled_back": True}
            db.undo.append(snap)
            db.dirty = True
            return {"ok": True, "created": created, "modified": modified, "transaction": p.get("description", ""), "saved": False}
        if ep == "setattrs":
            n = db.resolve(p["name"])
            snap = db.snapshot()
            db.els[n]["attrs"].update({k.upper(): str(v) for k, v in p["values"].items()})
            db.undo.append(snap); db.dirty = True
            return {"ok": True, "name": n, "readback": {k.upper(): db.els[n]["attrs"][k.upper()] for k in p["values"]}}
        if ep == "undo":
            steps = 0
            for _ in range(p.get("steps", 1)):
                if not db.undo:
                    break
                db.restore(db.undo.pop()); steps += 1
            db.dirty = bool(db.undo)
            return {"ok": True, "undone": steps}
        if ep == "view":
            db.resolve(p["name"])
            return {"ok": True, "command": f"AUTO {p['name']}"}
        if ep == "screenshot":
            return {"ok": True, "png_base64": _TINY_PNG}
        if ep == "savework":
            if p.get("confirm") != "SAVEWORK":
                return {"ok": False, "error": "confirmação ausente"}
            db.undo.clear(); db.dirty = False; db.saved += 1
            return {"ok": True, "saved": True, "comment": p.get("comment", "")}
        return {"ok": False, "error": f"endpoint desconhecido: {ep}"}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        if self.headers.get("X-E3D-Token") != TOKEN:
            self._send(401, {"ok": False, "error": "token inválido"}); return
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0) or b"{}")
        ep = self.path.removeprefix("/api/")
        try:
            self._send(200, handle(ep, body))
        except KeyError as e:
            self._send(200, {"ok": False, "error": str(e).strip("'\"")})

    def _send(self, code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def serve(port=8765):
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    s = serve(port)
    print(f"Ponte simulada em http://127.0.0.1:{port} (token: {TOKEN})")
    threading.Event().wait()

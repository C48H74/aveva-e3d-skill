"""E3D Live MCP — liga uma sessão AVEVA E3D aberta a um assistente de IA.

Cadeia:  Cliente MCP (Claude) -> este servidor (stdio) -> HTTP 127.0.0.1 + token
         -> add-in E3DLiveBridge dentro da sessão E3D do usuário (thread de UI).

Princípios (iguais aos do all3D-MCP):
  * atua como o próprio usuário, na sessão e permissões dele;
  * nunca grava (SAVEWORK) sem confirmação explícita do usuário;
  * toda escrita passa pelo loop: lint -> executar (transação desfazível)
    -> ler de volta -> verificar contra o documento -> corrigir ou reportar.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

from mcp.server.fastmcp import FastMCP, Image

try:  # execução como pacote ou como script
    from . import geometry, pml_lint
except ImportError:  # pragma: no cover
    import geometry, pml_lint  # type: ignore

HOST = os.environ.get("E3D_BRIDGE_HOST", "localhost")
PORT = int(os.environ.get("E3D_BRIDGE_PORT", "8765"))
TOKEN_FILE = Path(os.environ.get("E3D_BRIDGE_TOKEN_FILE",
                                 Path(os.environ.get("LOCALAPPDATA", Path.home())) / "E3DLiveBridge" / "token.txt"))
TIMEOUT = float(os.environ.get("E3D_BRIDGE_TIMEOUT", "120"))
GEOM_ATTRS = ["POS", "ORI", "DIAM", "HEIG", "XLEN", "YLEN", "ZLEN", "DTOP", "DBOT", "XBOT", "YBOT", "XTOP", "YTOP"]
SAVE_PHRASE = "SIM, GRAVAR"

mcp = FastMCP("e3d-live")


class BridgeError(RuntimeError):
    pass


def _token() -> str:
    tok = os.environ.get("E3D_BRIDGE_TOKEN")
    if tok:
        return tok.strip()
    try:
        return TOKEN_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        raise BridgeError(f"Token da ponte não encontrado em {TOKEN_FILE}. O E3D está aberto com o add-in E3DLiveBridge carregado?")


def call(endpoint: str, payload: dict | None = None) -> dict:
    req = urllib.request.Request(f"http://{HOST}:{PORT}/api/{endpoint}",
                                 data=json.dumps(payload or {}).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", "X-E3D-Token": _token()})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        raise BridgeError(f"Ponte E3D respondeu {e.code}: {body}") from None
    except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
        raise BridgeError(f"Sem conexão com a ponte E3D em {HOST}:{PORT} ({e}). Abra o E3D Design com o add-in carregado.") from None
    if not data.get("ok", False):
        raise BridgeError(data.get("error") or json.dumps(data, ensure_ascii=False))
    return data


def _err(e: Exception) -> dict:
    return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------- leitura

@mcp.tool()
def e3d_status() -> dict:
    """Estado da sessão E3D ao vivo: projeto, MDB, usuário, módulo, elemento corrente (CE) e se há mudanças não gravadas. Chame SEMPRE primeiro."""
    try:
        return call("health")
    except BridgeError as e:
        return _err(e)


@mcp.tool()
def e3d_get_element(name: str, attributes: list[str] | None = None) -> dict:
    """Lê um elemento (ex. '/P-101', 'CE') com atributos; inclui posição e orientação em relação ao mundo (WRT /*). attributes vazio = conjunto padrão."""
    try:
        return call("element", {"name": name, "attributes": attributes or []})
    except BridgeError as e:
        return _err(e)


@mcp.tool()
def e3d_list_members(name: str, depth: int = 1, element_type: str | None = None) -> dict:
    """Árvore de membros de um elemento até 'depth' níveis (máx. 6), opcionalmente filtrando por tipo (EQUI, PIPE, BRAN, NOZZ...)."""
    try:
        return call("members", {"name": name, "depth": max(1, min(depth, 6)), "type": element_type})
    except BridgeError as e:
        return _err(e)


@mcp.tool()
def e3d_collect(scope: str, element_types: list[str] | None = None, expression: str | None = None,
                attributes: list[str] | None = None, limit: int = 500) -> dict:
    """Coleta elementos abaixo de 'scope' por tipo e/ou expressão do E3D (ex. '( HBOR GE 100mm )'), devolvendo os atributos pedidos. Use para 'o que há nesta zona/volume'."""
    try:
        return call("collect", {"scope": scope, "types": element_types or [], "expression": expression,
                                "attributes": attributes or ["NAME", "TYPE"], "limit": min(limit, 5000)})
    except BridgeError as e:
        return _err(e)


@mcp.tool()
def e3d_find(pattern: str, element_type: str | None = None, scope: str | None = None, limit: int = 200) -> dict:
    """Procura elementos pelo nome com curinga (ex. '/P-40*', '*TANK*'), opcionalmente por tipo e escopo."""
    try:
        return call("find", {"pattern": pattern, "type": element_type, "scope": scope, "limit": limit})
    except BridgeError as e:
        return _err(e)


@mcp.tool()
def e3d_trace_connections(name: str) -> dict:
    """O que está ligado a um equipamento, bocal ou ramal: bocais, ramais conectados (HREF/TREF/CREF) e extremidades abertas."""
    try:
        return call("connections", {"name": name})
    except BridgeError as e:
        return _err(e)


@mcp.tool()
def e3d_evaluate(name: str, expression: str) -> dict:
    """Avalia uma expressão do E3D num elemento (ex. 'POS WRT /*', 'HBOR', 'NAME OF OWNER', 'MTOTUBE')."""
    try:
        return call("evaluate", {"name": name, "expression": expression})
    except BridgeError as e:
        return _err(e)


@mcp.tool()
def e3d_mto(scope: str, element_types: list[str] | None = None) -> dict:
    """Levantamento de material (MTO) agrupado por tipo + SPRE + diâmetro abaixo de 'scope'."""
    try:
        types = element_types or ["VALV", "ELBO", "TEE", "FLAN", "GASK", "REDU", "OLET", "CAP", "INST", "NOZZ"]
        data = call("collect", {"scope": scope, "types": types, "attributes": ["TYPE", "SPRE", "ABOR", "DESC"], "limit": 5000})
        cnt = Counter((r.get("TYPE", ""), r.get("SPRE", ""), r.get("ABOR", "")) for r in data["elements"])
        rows = [{"type": t, "spref": s, "bore": b, "qty": q} for (t, s, b), q in sorted(cnt.items())]
        return {"ok": True, "scope": scope, "lines": rows, "total": sum(cnt.values()), "truncated": data.get("truncated", False)}
    except BridgeError as e:
        return _err(e)


# ---------------------------------------------------------------- escrita (loop)

@mcp.tool()
def e3d_lint_macro(macro: str, allow_delete: bool = False) -> dict:
    """Valida uma macro PML1 SEM tocar no E3D (regras verificadas no E3D 3.1 + controle do usuário)."""
    return pml_lint.lint(macro, allow_delete).as_dict()


@mcp.tool()
def e3d_run_macro(macro: str, scope: str, description: str, allow_delete: bool = False) -> dict:
    """Executa uma macro PML1 na sessão ao vivo, dentro de uma transação desfazível e sem gravar.
    scope = elemento-pai onde a mudança acontece (ex. a ZONE). Passos automáticos: lint -> marca de undo
    -> execução -> leitura de volta do que foi criado/alterado com extensões geométricas.
    Depois disso chame e3d_verify com as cotas do documento de origem. allow_delete só com pedido explícito do usuário."""
    report = pml_lint.lint(macro, allow_delete).as_dict()
    if not report["ok"]:
        return {"ok": False, "stage": "lint", "lint": report,
                "next_step": "Corrija os erros de lint e chame e3d_run_macro de novo."}
    try:
        res = call("run", {"macro": macro, "scope": scope, "description": description})
    except BridgeError as e:
        return {"ok": False, "stage": "execute", "error": str(e), "lint": report,
                "next_step": "Leia o erro (linha/código do E3D), corrija a macro e repita. A transação foi abortada."}
    res["lint_warnings"] = report["warnings"]
    res["readback"] = _readback(res.get("created", []) + res.get("modified", []))
    res["next_step"] = ("Chame e3d_verify com checks tirados do desenho/especificação (cotas, contagens, ligações). "
                        "Se algo falhar, use e3d_undo ou corrija com nova macro. Nunca grave: a mudança fica pendente para o usuário.")
    return res


@mcp.tool()
def e3d_set_attributes(name: str, values: dict[str, str]) -> dict:
    """Altera atributos de um elemento (ex. {'DESC':'|Bomba|', 'SHOP':'TRUE'}) numa transação, e lê cada valor de volta."""
    try:
        return call("setattrs", {"name": name, "values": values})
    except BridgeError as e:
        return _err(e)


@mcp.tool()
def e3d_undo(steps: int = 1) -> dict:
    """Desfaz as últimas transações feitas pela ponte (não grava nada)."""
    try:
        return call("undo", {"steps": max(1, min(steps, 20))})
    except BridgeError as e:
        return _err(e)


@mcp.tool()
def e3d_verify(checks: list[dict]) -> dict:
    """Portão de verificação do loop. Compara o modelo AO VIVO com o esperado do documento.
    Tipos de check:
      {"type":"exists","element":"/X"}
      {"type":"attribute","element":"/X","attribute":"DIAM","expected":2134,"tolerance":1}
      {"type":"extent","element":"/X","axis":"U","min":152,"max":2286,"tolerance":1}   (eixo E|N|U, mm, mundo)
      {"type":"distance","from":"/A","to":"/B","axis":"E","expected":4369,"tolerance":1} (axis omitido = 3D)
      {"type":"count","scope":"/EQ","element_type":"NOZZ","expected":4}
      {"type":"connected","element":"/PIPE/B1","end":"head"|"tail"|"both"}
    Devolve pass/fail por check e o resumo. Só declare pronto com all_passed=true."""
    results, cache = [], {}

    def el(name):
        if name not in cache:
            cache[name] = call("element", {"name": name, "attributes": GEOM_ATTRS + ["HREF", "TREF", "HCON", "TCON"]})
        return cache[name]

    for i, c in enumerate(checks):
        r = {"index": i, "check": c}
        try:
            t = c.get("type")
            tol = float(c.get("tolerance", 1.0))
            if t == "exists":
                try:
                    el(c["element"]); r["passed"] = True
                except BridgeError as e:
                    r.update(passed=False, actual=str(e))
            elif t == "attribute":
                actual = el(c["element"])["attributes"].get(c["attribute"].upper())
                r["actual"] = actual
                r["passed"] = _match(actual, c["expected"], tol)
            elif t == "extent":
                e = el(c["element"])
                ext = geometry.extent(e["type"], geometry.parse_position(e["world"]["pos"]),
                                      geometry.parse_orientation(e["world"].get("ori")), _nums(e["attributes"]))
                lo, hi = ext[c["axis"].upper()]
                r["actual"] = {"min": lo, "max": hi}
                ok = True
                if "min" in c: ok &= abs(lo - float(c["min"])) <= tol
                if "max" in c: ok &= abs(hi - float(c["max"])) <= tol
                r["passed"] = ok
            elif t == "distance":
                a = geometry.parse_position(el(c["from"])["world"]["pos"])
                b = geometry.parse_position(el(c["to"])["world"]["pos"])
                if c.get("axis"):
                    k = "ENU".index(c["axis"].upper()); d = abs(b[k] - a[k])
                else:
                    d = sum((b[k] - a[k]) ** 2 for k in range(3)) ** 0.5
                r["actual"] = round(d, 3)
                r["passed"] = abs(d - float(c["expected"])) <= tol
            elif t == "count":
                data = call("collect", {"scope": c["scope"], "types": [c["element_type"]], "attributes": ["NAME"], "limit": 5000})
                r["actual"] = data["count"]
                r["passed"] = data["count"] == int(c["expected"])
            elif t == "connected":
                a = el(c["element"])["attributes"]
                ends = {"head": ["HREF"], "tail": ["TREF"], "both": ["HREF", "TREF"]}[c.get("end", "both")]
                r["actual"] = {k: a.get(k) for k in ends}
                r["passed"] = all(_is_ref(a.get(k)) for k in ends)
            else:
                r.update(passed=False, actual=f"tipo de check desconhecido: {t}")
        except (BridgeError, KeyError, ValueError) as e:
            r.update(passed=False, actual=f"erro: {e}")
        results.append(r)
    failed = [r for r in results if not r["passed"]]
    return {"ok": True, "all_passed": not failed, "passed": len(results) - len(failed), "failed": len(failed),
            "results": results,
            "next_step": "Pronto para revisão do usuário (não gravado)." if not failed else
            "Corrija só os itens que falharam (nova macro ou e3d_set_attributes) e rode e3d_verify de novo. Após 3 voltas sem sucesso, pare e reporte."}


@mcp.tool()
def e3d_view(name: str) -> dict:
    """Enquadra a vista 3D ativa no elemento (para o usuário conferir visualmente)."""
    try:
        return call("view", {"name": name})
    except BridgeError as e:
        return _err(e)


@mcp.tool()
def e3d_screenshot():
    """Captura a janela do E3D como imagem, para conferência visual do resultado."""
    try:
        data = call("screenshot", {})
    except BridgeError as e:
        return _err(e)
    import base64
    return Image(data=base64.b64decode(data["png_base64"]), format="png")


@mcp.tool()
def e3d_savework(comment: str, user_confirmation: str) -> dict:
    """Grava (SAVEWORK) as mudanças pendentes. SÓ use quando o usuário pediu para gravar NESTA conversa.
    user_confirmation deve ser exatamente 'SIM, GRAVAR', digitado pelo usuário."""
    if user_confirmation.strip().upper() != SAVE_PHRASE:
        return {"ok": False, "error": f"Gravação bloqueada: peça ao usuário para responder exatamente '{SAVE_PHRASE}'."}
    try:
        return call("savework", {"comment": comment, "confirm": "SAVEWORK"})
    except BridgeError as e:
        return _err(e)


# ---------------------------------------------------------------- utilidades

def _readback(names: list[str]) -> list[dict]:
    out = []
    for n in names[:200]:
        try:
            e = call("element", {"name": n, "attributes": GEOM_ATTRS})
        except BridgeError as ex:
            out.append({"name": n, "error": str(ex)}); continue
        row = {"name": n, "type": e["type"], "world_pos": e["world"].get("pos")}
        try:
            row["extent"] = geometry.extent(e["type"], geometry.parse_position(e["world"]["pos"]),
                                            geometry.parse_orientation(e["world"].get("ori")), _nums(e["attributes"]))
        except (ValueError, KeyError):
            pass
        out.append(row)
    return out


def _nums(attrs: dict) -> dict:
    out = {}
    for k, v in attrs.items():
        try:
            out[k] = geometry._num(str(v))
        except ValueError:
            pass
    return out


def _match(actual, expected, tol) -> bool:
    if actual is None:
        return False
    try:
        return abs(geometry._num(str(actual)) - float(expected)) <= tol
    except (ValueError, TypeError):
        norm = lambda s: re.sub(r"\s+", " ", str(s)).strip().strip("|'").upper()
        return norm(actual) == norm(expected)


def _is_ref(v) -> bool:
    return bool(v) and str(v).strip().upper() not in ("NULREF", "=0/0", "UNSET", "NULL", "")


def main():
    mcp.run()


if __name__ == "__main__":
    main()

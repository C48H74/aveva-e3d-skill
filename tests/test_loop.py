"""Testes offline do loop agir -> observar -> verificar -> corrigir, contra a ponte simulada.

Cenário = demo do all3D-MCP: tanque de propano 84" DI x 240" T/T, tampos de 23",
selas com passo de 172", fundo do casco a 6" do piso.
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["E3D_BRIDGE_PORT"] = "8799"
os.environ["E3D_BRIDGE_TOKEN"] = "mock-token"

from server import e3d_mcp as m, geometry, mock_bridge, pml_lint  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def bridge():
    srv = mock_bridge.serve(8799)
    yield
    srv.shutdown()


SHELL = "NEW CYLI /TANK/SHELL\nDIAM 2134\nHEIG 6096\nORI Z IS E AND Y IS U\nPOS E 0 N 0 U 1219\nEND\n"
SADDLES = ("NEW BOX /TANK/SAD-W\nXLEN 200\nYLEN 1800\nZLEN 300\nPOS E -2184.5 N 0 U 150\nEND\n"
           "NEW BOX /TANK/SAD-E\nXLEN 200\nYLEN 1800\nZLEN 300\nPOS E 2184.5 N 0 U 150\nEND\n")
CHECKS = [
    {"type": "extent", "element": "/TANK/SHELL", "axis": "U", "min": 152, "tolerance": 1},
    {"type": "extent", "element": "/TANK/HEAD-E", "axis": "E", "max": 3632, "tolerance": 1},
    {"type": "extent", "element": "/TANK/HEAD-W", "axis": "E", "min": -3632, "tolerance": 1},
    {"type": "distance", "from": "/TANK/SAD-W", "to": "/TANK/SAD-E", "axis": "E", "expected": 4369, "tolerance": 1},
    {"type": "count", "scope": "/TANK", "element_type": "DISH", "expected": 2},
    {"type": "attribute", "element": "/TANK/SHELL", "attribute": "DIAM", "expected": 2134},
]


def heads(e_rim):  # e_rim = posição em E do plano do aro do tampo leste
    return (f"NEW DISH /TANK/HEAD-E\nDIAM 2134\nHEIG 584\nORI Z IS E AND Y IS U\nPOS E {e_rim} N 0 U 1219\nEND\n"
            f"NEW DISH /TANK/HEAD-W\nDIAM 2134\nHEIG 584\nORI Z IS W AND Y IS U\nPOS E {-e_rim} N 0 U 1219\nEND\n")


def test_lint_rejeita_regras_de_ferro():
    bad = "NEW CYLI\nDIAM 10\nHEIG 10\nPOS E 0 N 0 U 0\nORI Z IS U\nEND\nSAVEWORK\nSUSPEND\n!x = 1\nNEW NOZZLE\nPOS E 0\nORI Y IS N\n"
    r = pml_lint.lint(bad)
    rules = {e.rule for e in r.errors}
    assert not r.ok and {"IR-2", "USER-CONTROL", "PML1", "IR-9a"} <= rules
    assert pml_lint.lint(SHELL).ok
    assert not pml_lint.lint("OLD /X\nDELETE CYLI\n").ok
    assert pml_lint.lint("OLD /X\nDELETE CYLI\n", allow_delete=True).ok


def test_geometria_datums():
    ori = geometry.parse_orientation("Z IS E AND Y IS U")
    assert geometry.extent("CYLI", (0, 0, 1219), ori, {"DIAM": 2134, "HEIG": 6096})["U"] == (152, 2286)
    assert geometry.extent("DISH", (3048, 0, 0), ori, {"DIAM": 2134, "HEIG": 584})["E"] == (3048, 3632)
    assert geometry.parse_position("W 5mm S 3m D 1in") == (-5, -3000, -25.4)
    x, y, z = geometry.parse_orientation("Z IS U AND X IS E 30 N")
    assert abs(x[1] - 0.5) < 1e-9


def test_loop_completo_tanque():
    assert m.e3d_status()["ok"]
    r = m.e3d_run_macro("NEW EQUI /TANK\nPOS E 0 N 0 U 0\nEND\n", "/ZONE-TEST", "equipamento")
    assert r["ok"] and r["created"] == ["/TANK"]

    # volta 1: erro de datum no DISH (POS no centro em vez do aro) -> verify falha
    r = m.e3d_run_macro(SHELL + heads(3048 + 292) + SADDLES, "/TANK", "tanque v1")
    assert r["ok"] and len(r["created"]) == 5 and r["saved"] is False
    v = m.e3d_verify(CHECKS)
    assert not v["all_passed"]
    falhas = {x["check"]["element"] for x in v["results"] if not x["passed"]}
    assert falhas == {"/TANK/HEAD-E", "/TANK/HEAD-W"}

    # corrigir só o que falhou
    fix = "OLD /TANK/HEAD-E\nPOS E 3048 N 0 U 1219\nOLD /TANK/HEAD-W\nPOS E -3048 N 0 U 1219\n"
    r = m.e3d_run_macro(fix, "/TANK", "corrige datum dos tampos")
    assert r["ok"] and set(r["modified"]) == {"/TANK/HEAD-E", "/TANK/HEAD-W"}
    v = m.e3d_verify(CHECKS)
    assert v["all_passed"], v

    # comprimento total = 7264 mm (286")
    e = r["readback"]
    assert {x["name"]: x["extent"]["E"] for x in e}["/TANK/HEAD-E"][1] == 3632


def test_erro_do_e3d_aborta_transacao():
    before = m.e3d_collect("/ZONE-TEST")["count"]
    r = m.e3d_run_macro("NEW CYLI /OK1\nDIAM 10\nHEIG 10\nEND\nNEW FOO /X\n", "/ZONE-TEST", "macro com erro")
    assert not r["ok"] and r["stage"] == "execute" and "Linha 5" in r["error"]
    assert m.e3d_collect("/ZONE-TEST")["count"] == before  # nada ficou pela metade


def test_undo_e_gravacao_protegida():
    r = m.e3d_run_macro("NEW BOX /TMP-BOX\nXLEN 1\nYLEN 1\nZLEN 1\nEND\n", "/ZONE-TEST", "temp")
    assert r["ok"]
    assert m.e3d_undo()["undone"] == 1
    assert not m.e3d_verify([{"type": "exists", "element": "/TMP-BOX"}])["all_passed"]
    assert not m.e3d_savework("teste", "sim")["ok"]
    assert m.e3d_savework("teste", "SIM, GRAVAR")["ok"]
    assert m.e3d_status()["pending_changes"] is False


def test_sem_ponte_mensagem_clara(monkeypatch):
    monkeypatch.setattr(m, "PORT", 1)
    r = m.e3d_status()
    assert not r["ok"] and "Abra o E3D" in r["error"]


def test_ferramentas_registradas_via_mcp():
    import asyncio
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def go():
        params = StdioServerParameters(command=sys.executable, args=["-m", "server.e3d_mcp"], cwd=str(ROOT))
        async with stdio_client(params) as (rd, wr):
            async with ClientSession(rd, wr) as s:
                await s.initialize()
                return {t.name for t in (await s.list_tools()).tools}

    names = asyncio.run(go())
    assert {"e3d_status", "e3d_run_macro", "e3d_verify", "e3d_undo", "e3d_savework", "e3d_trace_connections"} <= names
    assert len(names) == 16

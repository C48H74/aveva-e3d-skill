"""Validador estático de macros PML1 antes de enviar ao E3D.

Regras derivadas das "Iron Rules" verificadas no E3D Design Mk3.1.11.0
(NagisaCli/pml_master) e das regras de segurança do All3D-MCP
(a IA nunca grava o trabalho sozinha).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict

PRIMITIVES = {"CYLI", "CYLINDER", "CONE", "DISH", "BOX", "PYRA", "PYRAMID", "SNOU", "SNOUT", "CTOR", "RTOR"}
FORBIDDEN = [
    (r"^\s*SUSPEND\b", "SUSPEND não é comando do E3D e aborta a macro (IR-4)"),
    (r"^\s*RESUME\b", "RESUME não é comando do E3D e aborta a macro (IR-4)"),
    (r"^\s*VAR\s+0\b", "VAR 0 não é comando do E3D (IR-4)"),
    (r"^\s*ALPHA\s+HEADER\b", "ALPHA HEADER não é comando do E3D (IR-4)"),
    (r"^\s*ENDS\b", "ENDS não existe em PML1 (IR-5)"),
    (r"^\s*END\s+EQUI\b", "END EQUI não existe em PML1 (IR-5)"),
    (r"!!ALERT", "!!Alert abre diálogo modal e trava a sessão remota (IR-5)"),
    (r"^\s*COLLECT\b", "COLLECT não é PML1 (IR-5)"),
    (r"^\s*UNSET\b", "UNSET não é PML1 (IR-5)"),
    (r"^\s*!+[A-Z_][\w.]*\s*=", "Atribuição de variável PML2 numa macro PML1 (IR-5)"),
    (r"^\s*(NAME|DESC)\s*=", "Sintaxe 'ATRIBUTO =' é PML2; use 'DESC |texto|' (IR-5)"),
    (r"\$\$MACRO", "Use $M <arquivo>, nunca $$MACRO (IR-4)"),
]
USER_ONLY = [
    (r"^\s*SAVEWORK\b", "SAVEWORK é exclusivo do usuário (use e3d_savework com confirmação)"),
    (r"^\s*GETWORK\b", "GETWORK descarta o estado da sessão; só com pedido do usuário"),
    (r"^\s*QUITWORK\b", "QUITWORK descarta trabalho; só com pedido do usuário"),
    (r"^\s*(FINISH|EXIT)\b", "Fechar o E3D não é permitido pela ponte"),
]
DELETE_RX = r"^\s*DEL(ETE)?\b"


@dataclass
class Issue:
    line: int
    level: str  # "error" | "warning"
    rule: str
    text: str


@dataclass
class LintResult:
    ok: bool
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def as_dict(self):
        return {"ok": self.ok, "errors": [asdict(i) for i in self.errors], "warnings": [asdict(i) for i in self.warnings]}


def _strip_comment(line: str) -> str:
    i = line.find("--")
    return line if i < 0 else line[:i]


def lint(macro: str, allow_delete: bool = False) -> LintResult:
    errors, warnings = [], []
    lines = macro.splitlines()
    block = None  # {"type","start","seen":[...]}

    def close_block():
        if not block:
            return
        t, seen, start = block["type"], block["seen"], block["start"]
        if t in PRIMITIVES and "POS" in seen and "ORI" in seen and seen.index("POS") < seen.index("ORI"):
            errors.append(Issue(start, "error", "IR-2", f"{t}: ORI deve vir antes de POS (POS antes de ORI desloca o elemento sem erro)"))
        if t == "NOZZLE":
            if "CATR" not in seen:
                errors.append(Issue(start, "error", "IR-9a", "NOZZLE sem CATR SPCOMPONENT não desenha nada"))
            elif seen[0] != "CATR":
                errors.append(Issue(start, "error", "IR-9a", "NOZZLE: CATR deve ser o primeiro atributo após NEW NOZZLE"))
            if "POS" in seen and "ORI" in seen and seen.index("ORI") < seen.index("POS"):
                errors.append(Issue(start, "error", "IR-2", "NOZZLE: use POS antes de ORI (ordem inversa da dos primitivos)"))
            if block.get("bad_nozzle_ori"):
                warnings.append(Issue(start, "warning", "IR-2", "NOZZLE: oriente com 'ORI P1 IS <direção>'"))
        if t == "EQUI" and "POS" not in seen:
            warnings.append(Issue(start, "warning", "IR-7", "EQUI sem POS herda a posição do CE; use POS E 0 N 0 U 0 se os primitivos usam coordenadas absolutas"))
        if t in ("ELBOW", "BEND") and not ("ARRI" in seen and "LEAV" in seen):
            warnings.append(Issue(start, "warning", "PIPE-5a", f"{t} sem ARRI/LEAV explícitos pode gerar rota tracejada (mal definida)"))
        if t in ("ELBOW", "TEE", "VALVE", "FLANGE", "REDUCER", "GASKET", "OLET", "CAP", "BEND", "INSTRUMENT") and "SPRE" not in seen:
            warnings.append(Issue(start, "warning", "PIPE-4", f"{t} sem SPRE SPCOMPONENT: o componente fica sem catálogo"))

    for n, raw in enumerate(lines, 1):
        line = _strip_comment(raw).strip()
        if not line:
            continue
        up = line.upper()
        for rx, msg in FORBIDDEN:
            if re.search(rx, up):
                errors.append(Issue(n, "error", "PML1", msg))
        for rx, msg in USER_ONLY:
            if re.search(rx, up):
                errors.append(Issue(n, "error", "USER-CONTROL", msg))
        if re.search(DELETE_RX, up) and not allow_delete:
            errors.append(Issue(n, "error", "USER-CONTROL", "DELETE exige allow_delete=true, que só se usa com pedido explícito do usuário"))
        m = re.match(r"^NEW\s+([A-Z]+)", up)
        if m:
            close_block()
            block = {"type": m.group(1), "start": n, "seen": []}
            continue
        if re.match(r"^(END|OLD)\b", up):
            close_block()
            block = None
            continue
        if block:
            key = up.split()[0]
            if key in ("POS", "POSITION", "AT"):
                key = "POS"
            if key in ("ORI", "ORIENTATION"):
                key = "ORI"
                if block["type"] == "NOZZLE" and not re.search(r"P\d+\s+IS", up):
                    block["bad_nozzle_ori"] = True
            if key in ("CATR", "SPRE", "ARRI", "LEAV"):
                pass
            block["seen"].append(key)
    close_block()
    return LintResult(ok=not errors, errors=errors, warnings=warnings)


if __name__ == "__main__":
    import json, sys
    print(json.dumps(lint(open(sys.argv[1], encoding="utf-8").read()).as_dict(), indent=2, ensure_ascii=False))

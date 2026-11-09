# Instalação e roteiro de teste com o E3D real

## Arquitetura

```
Claude (Code ou Desktop) ──stdio──> server/e3d_mcp.py (16 ferramentas e3d_*)
        └─HTTP localhost:8765 + token──> E3DLiveBridge.dll (add-in dentro do E3D Design)
                                            └─ thread de UI → API .NET (Aveva.Core.*) + comandos PML
```

- Token aleatório criado a cada abertura do E3D, em `%LOCALAPPDATA%\E3DLiveBridge\token.txt`. Só aceita requisições locais.
- Macros temporárias ficam em `C:\Users\Public\E3DLiveBridge\work` (caminho sem espaços, por causa do `$M`).
- Escrita: `UndoTransaction` → `$M wrapper` → erro? `AbortTransaction` : `EndTransaction`. Nunca há `SaveWork` automático.

## Requisitos

- Windows com E3D Design licenciado (3.1 recomendado; a API `Aveva.Core.*` também existe na 2.1/2.10).
- .NET Framework 4.x (já vem no Windows). O `csc.exe` usado é `C:\Windows\Microsoft.NET\Framework\v4.0.30319`.
- Python 3.10 ou superior.

## Instalação

```powershell
cd <pasta e3d-live-mcp>
powershell -ExecutionPolicy Bypass -File install.ps1 -AvevaDesignExe "C:\AVEVA\Plant\Everything3D3.1"
claude mcp add e3d-live -- "C:\AVEVA\Custom\E3DLive\.venv\Scripts\python.exe" "C:\AVEVA\Custom\E3DLive\server\e3d_mcp.py"
```

O instalador compila o add-in, copia uma **cópia** do `DesignAddins.xml`, acrescenta a entrada e define `CAF_ADDINS_PATH` (variável de usuário). Se já existir uma customização da empresa em `CAF_ADDINS_PATH`, ele acrescenta a entrada lá e avisa.

Para desinstalar: remova a linha `E3DLiveBridge` do `DesignAddins.xml` copiado (ou apague `CAF_ADDINS_PATH`) e apague `C:\AVEVA\Custom\E3DLive`.

## Teste antes do E3D (já feito na nuvem)

`pytest tests` roda o loop inteiro contra a ponte simulada (`server/mock_bridge.py`): lint, execução, erro com rollback, verificação que reprova, correção, nova verificação, undo e gravação protegida. Para testar o MCP no PC sem E3D:

```powershell
python server\mock_bridge.py 8765          # terminal 1
set E3D_BRIDGE_TOKEN=mock-token & set E3D_BRIDGE_HOST=127.0.0.1   # terminal do Claude
```

## Roteiro com o E3D real — marcar cada item

Use um **projeto de treino** (SAMPLE/APS) e uma ZONE vazia. Nunca use projeto de produção no primeiro teste.

| # | Teste | Como | Esperado | Se falhar |
|---|---|---|---|---|
| T1 | Add-in carrega | Abrir o Design e olhar a janela de console | `[E3DLiveBridge] ouvindo em http://localhost:8765/` | Ver o caminho em `DesignAddins.xml`/`CAF_ADDINS_PATH`; DLL x86 |
| T2 | Status | "Qual o estado da sessão E3D?" | projeto, MDB e CE corretos | HttpListener sem permissão: `netsh http add urlacl url=http://localhost:8765/ user=%USERNAME%` |
| T3 | Leitura | "O que tem na ZONE X?" + "mostre POS e ORI de um equipamento" | árvore, `world.pos` em E/N/U | Avaliar `POS WRT /*` por PML |
| T4 | Execução simples **[TESTAR-E3D]** | "Crie um BOX 1000×500×200 em E0 N0 U100 na ZONE X" | `created` com o nome, verify ✓ | `$M /caminho` ou a navegação até o escopo |
| T5 | Erro capturado **[TESTAR-E3D]** | Macro com tipo inexistente (`NEW FOO`) | `ok:false`, texto do erro e nada criado | Se `handle any` não capturar o erro do `$M`, trocar o wrapper para a leitura do `!!error` |
| T6 | Rollback **[TESTAR-E3D]** | Macro que cria 1 BOX e depois erra | o BOX NÃO fica no modelo | `AbortTransaction` não cobre comando PML: usar `MARKDB`/`UNDO` PML |
| T7 | Undo **[TESTAR-E3D]** | "desfaça a última mudança" | o elemento some | `UndoTransaction.PerformUndo` |
| T8 | Datum DISH/CYLI | Fluxo A (tanque de propano) | todos os checks ✓ na 1ª ou 2ª volta | Registrar em `regras-pml.md` |
| T9 | Tubulação | Fluxo B com a spec do projeto de treino | ramal conectado, sem trechos tracejados | ARRI/LEAV, ordem dos componentes |
| T10 | Vista e imagem **[TESTAR-E3D]** | `e3d_view` + `e3d_screenshot` | a vista enquadra o elemento e a imagem chega | trocar `AUTO` pelo comando de limites da vista 3D |
| T11 | Proteção de gravação | Pedir "grave" sem a frase | bloqueado; com `SIM, GRAVAR` grava | — |

Ao final, cole o resultado da tabela na conversa. Cada falha vira uma correção na ponte e um registro em `regras-pml.md`.

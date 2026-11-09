# Ponte ao vivo — ferramentas e3d_* (E3D aberto)

> **Proveniência:** os princípios (sessão ao vivo, permissões do usuário, revisão antes de gravar) são do all3D-MCP. Os nomes de ferramenta, o protocolo de lint/transação e a frase "SIM, GRAVAR" são da implementação e3d-live-mcp, criada por nós. Ver `fonte-all3d-mcp.md`.

Só se aplica quando as ferramentas `e3d_*` estão disponíveis na sessão (servidor MCP
`e3d-live` + add-in `E3DLiveBridge` dentro do E3D Design). Se não estiverem, a skill
trabalha só em consulta, em geração de documentos e em planejamento, sem escrever.

## Antes de tudo

1. Chamar `e3d_status`. Se falhar, dizer: "O E3D precisa estar aberto no Design com o add-in E3DLiveBridge carregado" e parar.
2. Anotar projeto, MDB, CE e `pending_changes`. Se já houver mudanças pendentes de outra tarefa, avisar antes de empilhar.
3. Ler `normas-de-referencia.md` antes de montar qualquer macro.

## O loop (obrigatório em toda escrita)

```
ENTENDER → LER O MODELO → PLANEJAR → LINT → EXECUTAR → LER DE VOLTA → VERIFICAR → (CORRIGIR → VERIFICAR)×3 → REPORTAR
```

1. **Entender.** Extrair do documento de origem todas as cotas e quantidades, com unidade. Valor sem fonte vira Valor de Referência (N-02).
2. **Ler o modelo.** `e3d_find` / `e3d_list_members` / `e3d_collect`: o elemento já existe? Qual zona recebe? Qual spec e quais componentes existem? (N-04, N-08, N-09)
3. **Planejar.** Tabela de coordenadas (ponto, E/N/U, o que acontece ali). Definir o datum de cada primitivo antes de calcular POS (N-11, N-12).
4. **Escrever a macro PML** e passar por `e3d_lint_macro`. Erro de lint = corrigir, nunca contornar.
5. **Executar** com `e3d_run_macro(macro, scope=<ZONE ou EQUI>, description=...)`. Roda numa transação desfazível: se der erro, aborta, nada fica pela metade, e o erro volta com a linha.
6. **Ler de volta.** O resultado traz `created`/`modified` e o `readback` com a extensão geométrica real.
7. **Verificar** com `e3d_verify(checks)`, montando os checks a partir do **documento de origem** (N-03): `extent` (comprimento, elevação, folga), `distance` com `axis` (passo de suportes), `count` (bocais, válvulas), `connected both` (ramal fechado), `attribute` (diâmetro, spec, atributos de identificação).
8. **Corrigir** no máximo 3 vezes. Depois disso, parar e reportar o que falhou e o que foi tentado.
9. **Gravar** só se o usuário responder exatamente **"SIM, GRAVAR"** (N-21). Antes disso, dizer: "nada foi gravado".

## Regras de PML já confirmadas em fonte

- Tampo (DISH) pelo aro, não pelo centro (N-12).
- ORI antes de POS (N-11).
- Bocal precisa da referência de catálogo primeiro (N-10).

Fontes: NagisaCli/pml_master (E3D 3.1). Status: **[TESTAR-E3D]**, a confirmar na primeira
rodada real.

## Testes pendentes (quando o E3D estiver disponível)

- Erro dentro da macro é capturado e a transação desfaz tudo (crítico).
- `e3d_lint_macro` bloqueia comando de gravar.
- Mudanças pendentes aparecem em `pending_changes`.
- Os demais itens do roteiro T1–T11 ainda não foram executados.

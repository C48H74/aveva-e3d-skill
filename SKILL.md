---
name: aveva-e3d-modelling
description: >
  Modelar, consultar e revisar plantas industriais no AVEVA Everything3D (E3D):
  tubulação, equipamentos, suportes (MDS), eletrocalhas, desenhos, P&ID e Schematic
  3D Integrator. Usar em qualquer etapa de modelagem E3D/PDMS, em isométricos ou
  MTO saídos do modelo, e em verificação de modelo contra desenho. Quando as
  ferramentas e3d_* estiverem disponíveis, também atua no E3D aberto, em loop com
  validação. Funciona em qualquer projeto: não traz padrão exclusivo de cliente.
---

# AVEVA E3D — modelagem com normas e validação

Skill de execução para modelar e revisar plantas no AVEVA E3D. Narrativa em português;
comandos, formulários, atributos e classes de elemento ficam em inglês, como no software.

## Três modos de trabalho

| Modo | Quando | O que usa |
|---|---|---|
| **Consulta** | Perguntar algo sobre o E3D, o modelo ou um documento | `references/` |
| **Planejamento / documento** | Montar lista, verificar cotas, preparar dados de modelagem | `references/` + normas |
| **Ao vivo** | Modelar ou alterar o E3D aberto | `references/ponte-ao-vivo.md` (só com as ferramentas `e3d_*`) |

Antes de escrever no modelo, identificar o modo. Sem as ferramentas `e3d_*`, a skill
nunca tenta escrever: trabalha em consulta e planejamento.

## Princípios do all3D-MCP (fonte oficial)

O site do produto (aila.ai/all3d-mcp) afirma que o assistente atua na sessão E3D ativa,
com as permissões do próprio usuário e sem serviço privilegiado. As alterações ficam
pendentes até o usuário revisar e aceitar; o assistente não faz commit sozinho. Consulta,
construção e comparação com desenhos e especificações são as capacidades citadas. Detalhes
técnicos e nomes de ferramentas não são públicos: ver `references/fonte-all3d-mcp.md`.

Nomes `e3d_*` e a frase "SIM, GRAVAR" são da implementação e3d-live-mcp, não do all3D.

Exemplo de consulta típica: "What's piped or wired to this equipment, and what's left unconnected?"

## Normas são limites, não padrão

Toda decisão de modelagem passa pelo catálogo de `references/normas-de-referencia.md`
(itens N-01 a N-21). Os níveis são:

- **BLOQUEIO**: não executa. Só segue com autorização explícita e registrada.
- **LIMITE**: passa de valor-limite da norma ativa. Informa e pergunta: seguir, ajustar ou registrar exceção.
- **CONFIRMAR**: falta dado. Rotula como Valor de Referência ou pergunta. Nunca completa de memória.
- **ORIENTAÇÃO**: boa prática, sem bloqueio.

A **norma ativa** é escolhida pelo usuário no início da tarefa. A skill não assume nenhuma.
Se a norma ativa não define um valor, a skill pergunta, sem chutar.

## Mental model

E3D é orientado a dados. Tudo é um elemento com nome numa hierarquia, e os documentos são
extraídos do modelo, nunca editados.

```
WORLD
└── SITE            projeto
    └── ZONE        área de disciplina (Purpose define o uso; suporte exige SUPP)
        └── elementos (PIPE, BRANCH, EQUI, SUPPO, ANCI, CABLE…)
```

Três consequências:

1. **O modelo é a fonte.** O 2D é uma vista. Revisa-se o modelo e reemite-se o documento (N-01).
2. **Edição é exclusiva.** Elemento claimed por outro usuário não pode ser editado (N-06).
3. **Nome é dado.** Tags e sufixos alimentam os relatórios. Nome errado gera MTO errado.

## Rotas de referência

Referências de modelagem por disciplina (tubulação, equipamento, suportes, eletrocalha, desenho, P&ID) não são distribuídas aqui. Elas dependem de fontes com licença compatível e serão adicionadas quando isso estiver confirmado.

| A tarefa | Ler |
|---|---|
| Limites e normas de modelagem | `references/normas-de-referencia.md` |
| Origem do all3D-MCP: o que é oficial e o que não é | `references/fonte-all3d-mcp.md` |
| Execução no E3D aberto | `references/ponte-ao-vivo.md` |

## Mapa de módulos (visão geral)

| Aplicação | Produz | Entrega para |
|---|---|---|
| **Piping** | geometria `PIPE`/`BRANCH`, conexões | Draw (isométricos), Supports, Integrator |
| **Equipment** | `EQUI` com primitivas e bocais | Piping (conectar ao bocal), Draw |
| **Supports** | `SUPPO` + `ANCI` sob MDS | isométricos, lista de suportes, MTO |
| **Cable Tray** | eletrocalha física com `FTUB` | Draw |
| **Cableway & Cable** | espaço reservado, cabos, % de ocupação | Cable Tray |
| **Draw** | folhas, vistas, cotas | PDF / DXF / DWG |
| **PID Designer** | esquema no banco Schematic | Schematic 3D Integrator |
| **Schematic 3D Integrator** | conciliação esquema × 3D | fecha o ciclo |

Pares que se confundem: **Cable Tray × Cableway** (uma é a peça física, a outra é espaço e cabo);
**PID Designer × Schematic 3D Integrator** (um escreve o esquema, o outro confere com o 3D).

## Ordem típica de projeto

1. Interface e defaults: unidades, simbologia, Application Defaults.
2. Hierarquia: `SITE` → `ZONE`, com o Purpose certo por disciplina.
3. Estrutura e civil: primitivas, pisos, paredes.
4. Equipamento: `EQUI` + primitivas + bocais.
5. Tubulação: `PIPE` → `BRANCH` → componentes.
6. Suportes na zona `SUPP`.
7. Elétrica e instrumentação: cableway, cabos, eletrocalhas.
8. Verificação: clash, consistência de dados.
9. Documentos: isométricos, desenhos, lista de suportes, MTO.
10. Integração: conciliar com o P&ID.

## Laço de trabalho

**Antes de tocar no modelo**

1. Confirmar `SITE`, `ZONE`, spec e norma ativa (N-04, N-09). Perguntar se a norma ativa não estiver definida.
2. Verificar claim do elemento (N-06).
3. Para suportes: confirmar Purpose `SUPP` (N-05) e informar que o autonaming é consumido ao iniciar (N-07).

**Durante a modelagem**

4. Modelar a partir do documento de origem na revisão atual (N-02).
5. Usar o formulário do sistema sempre que houver um (N-13).
6. Nomear o elemento logo após criá-lo.

**Depois da modelagem**

7. Rodar clash e resolver o que foi introduzido (N-20).
8. Reextrair saídas e conferir o **log**, não só o arquivo (N-19).
9. Não deixar nada claimed.

## Regras de ouro

- **Nunca editar o 2D.** Revisar o modelo e reemitir (N-01).
- **Não criar elemento fora da zona certa** para contornar relatório. Criar na zona correta (N-04).
- **Formulário do sistema, sempre.** Edição fora dele não entra em lista nem MTO (N-13).
- **Tag é dado.** Fora do padrão, o relatório sai errado.
- **Log limpo antes do MTO** (N-19).
- **Claim é bloqueio.** Lote pula elemento claimed sem avisar (N-06).
- **Autonaming é consumido ao iniciar.** Cancelar deixa buraco na numeração (N-07).

## Vocabulário que os manuais não usam

| Não diga | Diga |
|---|---|
| `ATTA`, `HANG`, `REST`, `GUID` para suportes | `SUPPO`, `SUPC`, `ANCI`, `VSPR`. `ATTA` só existe em penetração de tubulação |
| *gap* (P&ID × 3D) | **Difference**, **Error**, **Not Matched**, **Unresolved branches** |
| *Validate* no Diagrams | **Consistency Check** |
| *Palette* no Diagrams | **Shapes** / stencil |
| *Sheet* no Diagrams | **pages** |
| associações como *constraint solver* | são **passivas**, não resolvem sozinhas |
| "desenhar a vista" | **criar uma View** sobre o modelo |

Termo fora dos manuais: dizer que veio de outro módulo, de PDMS ou de vocabulário de projeto,
em vez de inventar equivalência.

## Siglas principais

| Termo | O que é |
|---|---|
| `SITE` | container do projeto (a planta) |
| `ZONE` | área de disciplina dentro do site |
| `PIPE` / `BRANCH` | linha / trecho navegável da linha |
| `EQUI` | equipamento |
| `SUPPO` / `ANCI` | suporte / peça de fixação principal |
| `VSPR` | mola dentro de um hanger |
| MDS | AVEVA Model Data Server: camada de catálogo e automação de suportes |
| MTO | lista de materiais extraída do modelo |
| Isométrico | desenho isométrico extraído da linha |



## Limites desta skill

- Não cobre cálculo estrutural detalhado, HVAC, elétrica além de eletrocalha e cableway, nem administração do catálogo MDS — fora do escopo deste repositório.
- Comportamentos marcados **[TESTAR-E3D]** ainda não foram confirmados no E3D real.

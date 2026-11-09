# Normas de referência — limites da modelagem

Esta skill **não traz um padrão exclusivo**. Ela roda em qualquer projeto. As normas
abaixo são **limites**: definem o que pode ser feito sem perguntar e o que exige
informar ou perguntar. Os valores numéricos vêm da **norma ativa do projeto**,
escolhida pelo usuário no início. Quando a norma ativa não define um valor, a skill
**não assume**: pergunta.

## Como os limites funcionam

| Nível | Quando | O que a skill faz |
|---|---|---|
| **BLOQUEIO** | Violação que quebra o modelo, o relatório ou a rastreabilidade | Não executa. Só segue com autorização explícita e registrada do usuário. |
| **LIMITE** | Passa de um valor-limite da norma ativa | Informa o valor, a norma e o desvio. Pergunta: seguir, ajustar ou registrar exceção. |
| **CONFIRMAR** | Falta dado (valor não vindo do documento, norma sem valor, spec não identificada) | Rotula como **Valor de Referência** ou pergunta antes de modelar. Nunca preenche sozinha. |
| **ORIENTAÇÃO** | Boa prática, sem efeito no relatório | Menciona, sem bloquear. |

Regra geral: **se a norma ativa não diz, a skill pergunta. Não completa de memória.**

## Catálogo de limites

Fonte indicada em cada item. `[TESTAR-E3D]` = comportamento ainda não confirmado no
E3D real; tratar como hipótese até o teste.

### Fonte e rastreabilidade

- **N-01 · BLOQUEIO · Modelo é a fonte.** Nunca editar o 2D. Revisão se faz no modelo e o documento é reemitido. *(manuais de Draw e de hierarquia)*
- **N-02 · BLOQUEIO · Documento de origem.** Parâmetros de modelagem vêm do desenho, isométrico, P&ID, folha de dados ou pedido, na revisão atual. Nunca da memória. Se não estiver no documento, é **CONFIRMAR** (Valor de Referência rotulado). *(prática geral)*
- **N-03 · BLOQUEIO · Verificação contra o documento.** A verificação compara o modelo com o documento de origem, nunca com a própria macro que o gerou. *(regra da skill live)*

### Hierarquia e posse

- **N-04 · BLOQUEIO · Zona correta.** Elemento na zona errada existe, mas os relatórios não o enxergam. Confirmar `SITE` e `ZONE` antes de qualquer escrita. *(hierarquia do E3D)*
- **N-05 · BLOQUEIO · Purpose da zona.** Suportes só em zona com Purpose `SUPP`. *(manual de Supports, TM-1818)*
- **N-06 · BLOQUEIO · Claim.** Elemento reivindicado por outro usuário não pode ser editado. Operações em lote pulam elemento claimed sem avisar, então conferir o resultado. *(manual de Pipework/Supports)*
- **N-07 · CONFIRMAR · Autonaming.** O sequencial é consumido ao iniciar; cancelar cria buraco na numeração. Informar antes de iniciar um lote. *(manual de Supports)*

### Catálogo e especificação

- **N-08 · BLOQUEIO · Componente de catálogo.** Nunca inventar `SPCOMPONENT` ou outro código de catálogo. Procurar o existente (`e3d_find` ou equivalente). Se não existir, perguntar. *(regra da skill live)*
- **N-09 · CONFIRMAR · Spec.** Modelar com a spec que o projeto usa (`PSPE`/`SPRE` ou equivalente). Spec errada gera modelo que não pode ser comprado. *(manual de Pipework)*
- **N-10 · BLOQUEIO · Referência de bocal.** Bocal de equipamento precisa da referência de catálogo antes de posicionar. *(regra PML, [TESTAR-E3D])*

### Geometria e PML

- **N-11 · BLOQUEIO · Ordem ORI antes de POS.** Em primitivas, orientação antes da posição. *(regra PML, [TESTAR-E3D])*
- **N-12 · BLOQUEIO · Datum do tampo.** O tampo (DISH) é posicionado pelo aro, não pelo centro. Erro deixa o tampo flutuando. *(regra PML, [TESTAR-E3D])*
- **N-13 · BLOQUEIO · Formulário do sistema.** Geometria editada fora do formulário não entra na lista de suportes nem no MTO. Usar o formulário quando existir. *(manuais de Pipework e Supports)*
- **N-14 · CONFIRMAR · Unidades.** Converter polegadas para mm (× 25,4) e mostrar a conversão. *(prática da skill live)*

### Limites numéricos (valor vem da norma ativa)

- **N-15 · LIMITE · Espaçamento entre suportes (vão).** Comparar com o vão máximo da norma ativa. Se não houver norma, perguntar. *(valor: norma ativa)*
- **N-16 · LIMITE · Elevação e folga ao piso.** Comparar com as cotas do documento e com a folga mínima da norma ativa. *(valor: norma ativa)*
- **N-17 · LIMITE · Distância de drenos, respiros, válvulas e instrumentos.** Comparar com a distância mínima da norma ativa. *(valor: norma ativa)*
- **N-18 · LIMITE · Comprimento total e quantidades.** Divergência entre modelo e documento acima da tolerância da norma ativa. *(valor: norma ativa)*

### Saída de documentos

- **N-19 · BLOQUEIO · Log limpo antes de MTO e isométrico.** Conferir o log de extração antes do arquivo final. Log com erro = MTO inválido. *(manual de Supports)*
- **N-20 · ORIENTAÇÃO · Clash antes de emitir.** Rodar verificação de interferência antes de emitir isométrico ou lista. *(manual de Supports e Pipework)*

### Gravação

- **N-21 · BLOQUEIO · Gravar só com confirmação.** Nunca gravar no banco (SAVEWORK) sem a frase exata do usuário. Padrão da skill live: **"SIM, GRAVAR"**.
- **N-22 · BLOQUEIO · Permissão do próprio usuário.** A skill age só com as permissões e a sessão do usuário que está conectado. Não usar credencial de outra conta, não contornar SSO, não operar como serviço privilegiado. *(all3D-MCP, site oficial)*
- **N-23 · BLOQUEIO · Sem commit automático.** Toda alteração fica pendente até o usuário revisar e aceitar. A skill não finaliza nem commita por conta própria. *(all3D-MCP, site oficial)*

## O que fazer quando um limite é atingido

1. Informar: o item (N-xx), o valor encontrado, o valor-limite e a fonte da norma.
2. Perguntar, em uma frase: seguir o limite, ajustar o modelo ou registrar exceção com justificativa.
3. Registrar a decisão no resumo final, junto com o item.
4. Não seguir adiante em BLOQUEIO sem a autorização registrada.

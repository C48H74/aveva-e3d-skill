# O que foi aprendido e de onde

## all3D-MCP (aila.ai/all3d-mcp, all3D Oy, Finlândia)

A página é de marketing: não tem API pública, documentação, preço nem código (é WordPress/Elementor; o único "API" é o wp-json do próprio site). O conteúdo técnico saiu dos **2 vídeos de demonstração** hospedados na página:

- **Demo Propane Tank:** o assistente confere se a sessão está ativa no Design e se o tanque já existe (`Find Elements`), lê o desenho e resume as cotas numa linha, monta tudo numa passada (`Run Macro`, 172 ms), verifica a geometria contra o desenho com uma lista ✓ (comprimento total, folga ao piso, passo das selas, família dos bocais), enquadra a vista (`Set Camera`) e aceita um ajuste por conversa ("uma PYRA por perna"). Depois, no módulo Draw, cria uma folha A3 com 4 vistas e um quadro de dados (`New Drawing`) e abre a folha para conferir (lê a imagem).
- **Demo isométrico:** a partir de uma foto de isométrico à mão, o assistente recupera notas anteriores (memória), descobre a spec e a referência de coordenadas, monta a tabela de pontos (canto, válvula, sentido do fluxo), cria PIPE/BRANCH e depois os componentes em 2 macros, re-tessela e verifica (tubos sólidos sem trechos tracejados, válvulas orientadas, pilhas de flange sem sobreposição). Termina com "Tudo NÃO gravado (MARKDB). Rode SAVEWORK". Em seguida aplica SHOP=TRUE às 6 curvas e verifica na 1ª e na 6ª.
- **Princípios declarados:** a IA nunca grava sozinha; atua como o usuário, dentro da sessão e das permissões dele; usa SSO; trabalha sempre com o modelo ao vivo, sem exportações velhas; segue o padrão aberto MCP.
- **Ferramentas vistas na tela:** Find Elements, Run Macro, Set Camera, New Drawing, leitura de imagem, painel "EasyMCP" acoplado no E3D.

## Repositórios usados (GitHub)

| Repositório | O que foi aproveitado |
|---|---|
| NagisaCli/pml_master | Iron Rules (datum, ordem ORI/POS, NOZZLE/CATR, PML1 puro), sintaxe PIPE/BRANCH, e a ideia de transação + leitura de volta + `AbortTransaction` do `integrations/e3d_live` |
| nhdang117/PMLNet.Learning | API .NET verificada no E3D 3.1 (DbElement, filtros, UndoTransaction, IAddinInjected, registro do add-in) |
| nitin-121/aveva-e3d-mcp | Formato MCP (Python) + ponte REST em C#, catálogo de ferramentas (grafo, MTO, spec check). **Diferença:** ele roda em modo Standalone (sem a sessão aberta) e grava automaticamente em clone/bulk; aqui a ponte é ao vivo e não grava |
| domado01/aveva-e3d-customisation | Padrão para marshalar chamadas HTTP para a thread de UI do E3D (`Control.Invoke`) |
| GeorgGrebenyuk/aveva_e3d_pythonshell, djee79/pml-lsp, k-awata/pjma | Referências complementares (console IronPython, LSP de PML, gestão de projetos) |

## Ferramentas instaladas para este trabalho

- **API Anything** (goodnight000/api-anything): instalado no modo local-only, sem compartilhar nada. Testado com `call hacker-news search` → `ok:true, tier:1`.
- **reverse-engineering** (plutolaboratories/skills): usado para mapear o site (HTML, scripts, endpoints wp-json, mídia) e achar os vídeos.

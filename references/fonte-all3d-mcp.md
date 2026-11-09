# Fonte: all3D-MCP — o que o site oficial afirma

Fonte primária: https://aila.ai/all3d-mcp/ (landing page do produto, do fabricante all3D Oy / AILA.ai).
Consultada em 2026-11-08. Tudo abaixo é o que o site afirma. O que não está listado aqui não é do produto.

## O que o site afirma

- Liga uma sessão **ativa** do AVEVA E3D a um assistente de IA, por meio do **MCP** (Model Context Protocol).
- Atua **dentro da sessão** e **com as permissões do próprio usuário**, sem serviço privilegiado separado.
- Login por **SSO** da organização.
- As alterações ficam **não commitadas** até o usuário revisar e aceitar. O assistente **não faz commit por conta própria**.
- Os desenhos também são finalizados e conferidos pelo usuário.

### Capacidades de consulta
- Rastrear conexões de tubulação e elétricas e identificar pontos não conectados.
- Verificar dimensões, comprimentos, pesos e propriedades.
- Explorar o conteúdo de uma zona ou volume.
- Resumir em linguagem natural o estado de uma parte do modelo.
- Comparar o modelo com desenhos e especificações.

### Capacidades de construção e alteração
- Criar componentes (o site cita válvulas) conforme a especificação do projeto.
- Mover, reorientar e ajustar atributos.
- Apoiar desenhos 2D: vistas, cotas, rótulos, tabelas de MTO e revisões.
- Montar equipamentos, suportes e conexões numa zona a partir de descrição.

### Exemplo de pergunta citado
"What's piped or wired to this equipment, and what's left unconnected?"

### Empresa
all3D Oy, Pori, Finlândia. CEO Markus Helmle. Contato: aila@all3d.fi.

## O que o site NÃO informa

- Nomes e parâmetros das ferramentas (tools).
- Passos de instalação, requisitos, versões do E3D, configuração da conexão.
- Arquitetura interna, limites, preços, planos.
- Documentação, repositório, changelog, vídeos incorporados.
- Único caminho indicado: "Book a Demo" (e-mail acima).

## Outras fontes verificadas

- **AILA.ai** (aila.ai): produto de engenharia com IA. Cita o all3D-MCP como "AI in your live AVEVA E3D session". Implantação local, isolada (air-gapped) ou em nuvem. Sem detalhe técnico de MCP.
- **all3D Oy**: vende o EasyTools, toolkit para AVEVA, com licença pela própria empresa.
- **Fórum AVEVA** (tópico "AVEVA E3D MCP"): discussão de 9 mensagens. Sem nomes de ferramenta. A AVEVA a apresenta como funcionalidade em investigação, possivelmente no roadmap.
- **AVEVA World 2026, Milão** (sessão "Unlock your data with the power of AI and MCP"): palestra da própria AVEVA sobre MCP com produtos AVEVA. Sem detalhe técnico público.
- **Sitemap do aila.ai**: não foi possível listar as páginas. O conteúdo retornado não é utilizável.

## Consequência para esta skill

- Os **princípios** (sessão ao vivo, permissões do usuário, sem commit automático, revisão humana, consulta e comparação com desenhos) são do all3D-MCP, conforme o site.
- A **lista de ferramentas** `e3d_*`, o protocolo de lint/transação e a frase de gravação "SIM, GRAVAR" **não são do all3D**. São da implementação e3d-live-mcp, criada por nós. O all3D não documenta nomes de ferramentas.
- Para documentação técnica do all3D, o único caminho público é contato direto com o fabricante.

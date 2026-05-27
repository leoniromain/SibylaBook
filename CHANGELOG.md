# Changelog

Todas as alterações relevantes do Sibyla estão documentadas aqui.

---

## [0.2.0] — 2026-05-25

### Arquitetura — Unificação em processo único

- **Removido FastAPI / Uvicorn** — o app não expõe mais nenhuma porta HTTP
- Todo o código de backend foi integrado diretamente ao pacote `sibyla/` e importado pelo processo da UI via Python puro
- Comunicação UI ↔ lógica de negócio agora é chamada direta de funções (sem HTTP, sem sockets)
- `backend/` e `ui/` removidos; substituídos por `sibyla/core/` e `sibyla/qt/`
- Único ponto de entrada: `python run.py` (ou `./dev.sh` / `.\dev.ps1`)
- Único `.venv` na raiz do projeto com Python 3.11

### Sidebar de Grupos

- **Pastas e divisores** coloridos no painel lateral esquerdo
- Criação, edição e exclusão via menu de contexto (clique com botão direito)
- **Drag-and-drop** para reordenar grupos no sidebar
- **Arrastar livro para pasta** — adiciona a tag da pasta ao livro automaticamente; salvo em `~/Sibyla Library/library.json`
- Clique em qualquer pasta ou divisor filtra a biblioteca para mostrar somente os livros daquele grupo
- Sub-pastas e sub-divisores aninhados com indentação
- **Contador** de livros exibido ao lado de cada item (sempre visível, inclusive quando 0)
- Grupos persistem em `~/.sibyla/sidebar_groups.json`

### Biblioteca

- **"Mover para…"** no menu de contexto do livro — lista todas as pastas e divisores; marca com ✓ o grupo atual; opção "Sem pasta" para remover de qualquer grupo
- Sidebar atualiza contagens automaticamente após mover, remover ou importar livros
- Chips de tag removidos da grade (filtragem centralizada no sidebar)
- Botão "Selecionar" e seleção múltipla para adicionar vários livros à fila de uma vez
- Ordenação por título, autor, data e avaliação

### Visual

- **Bolinhas uniformes** — todos os itens do sidebar (Todos, Avulsos, pastas, divisores) usam o mesmo círculo pintado de 16 px via QPainter (antialiasing real, sem emoji)
- Tamanho único controlado pela constante `_ICON_SIZE` em `reading_layout.py`
- **Tema claro / escuro** alternável pelo botão 🌙 / ☀️ na barra superior; preferência salva em `QSettings`
- Barra superior totalmente clara no tema claro (sem resquícios de cor escura)
- Empty state da biblioteca permanece na posição correta (header e busca fixos no topo independente de haver livros)
- Menus de contexto do sidebar sem ícones

### Leitor

- Leitor de PDF embutido (renderização via PyMuPDF em thread separada)
- Leitor de EPUB embutido (extração de capítulos via ebooklib)
- Navegação por teclado (setas, Page Up/Down)
- Abrir livro em janela flutuante independente
- Redimensionamento automático da página ao redimensionar a janela

### Configuração

- Configurações salvas em `~/.sibyla/config.json`
- Removidas opções de host/porta (não há mais servidor)
- Tema: somente claro ou escuro (opção "padrão" removida)

---

## [0.1.0] — 2026-05-15

### Novas Funcionalidades

#### Biblioteca
- Grade de cards responsiva com capa, título, autor e badge de formato
- Extração automática de capa (PDF via PyMuPDF, EPUB via OPF)
- Extração de metadados (título, autor, idioma) no import
- Busca em tempo real por título ou autor; filtros por formato e status de tradução
- Import de múltiplos arquivos com opção de copiar para `~/Sibyla Library/books/`
- Menu de contexto: abrir, adicionar à fila, editar metadados, remover
- Editor de metadados completo (título, autor, idioma, tags, avaliação, status de leitura, série)
- Marcação automática como "traduzido" após conclusão do job

#### Fila de Tradução
- Tela dedicada com cards por job: status, progresso, log expandível
- Processamento sequencial; próximo job inicia automaticamente
- Pausa (salva até a última página), retomada, cancelamento
- Botão "Ver na pasta" para revelar o arquivo no Finder / Explorer
- Botão "Limpar concluídos"
- Badge "⏳ Fila (N)" na navegação atualizado em tempo real
- Estado da fila persistido em `~/.sibyla/queue_state.json`; restaurado ao reabrir

#### Tradução Incremental
- Todas as saídas (DOCX, PDF, TXT, MD) gravadas após cada página traduzida
- Cancelar ou pausar nunca perde páginas já concluídas

#### Configurações
- Campo de pasta da biblioteca com botão de seleção
- Recarregamento de configurações ao navegar para as abas Traduzir e Biblioteca

### Melhorias
- Estilo Fusion aplicado globalmente (corrige QComboBox em branco no macOS)
- Tela de configurações redesenhada com larguras fixas

### Correções
- Deadlock no cancelamento (sinal emitido com lock ativo)
- Congelamento da UI em pause/cancel (chamadas de rede na thread principal)
- Crash `NoneType` quando `translator.translate()` retorna `None`
- Overflow de imagem no PDF de saída

---

## [0.0.x] — Era pré-biblioteca

Versões iniciais: tradução de PDF/EPUB com Google Translate, agrupamento por página com marcadores `⟦N⟧` (~10× mais rápido que bloco a bloco), opções de alinhamento/fonte/tamanho, saídas DOCX/PDF/TXT, histórico de traduções, scripts de build com PyInstaller.

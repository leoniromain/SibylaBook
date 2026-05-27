# Sibyla Translate

Leitor e tradutor de PDFs e EPUBs com gerenciamento de biblioteca.  
Roda em **macOS** e **Windows** sem dependências de serviços externos.

## Funcionalidades

- **Biblioteca** — grade de cards com capa, título, autor e formato
- **Leitura integrada** — leitor de PDF (página a página) e EPUB (capítulo a capítulo)
- **Tradução** — PDFs e EPUBs com preservação de layout; saída em `.docx`, `.pdf`, `.txt` ou `.md`
- **Fila de tradução** — procesamento sequencial com progresso por página, pausa e retomada
- **Sidebar de grupos** — pastas e divisores coloridos; arraste livros para organizar
- **Histórico** de traduções concluídas
- **Tema claro / escuro** alternável pelo botão da barra superior
- Detecção automática do idioma de origem

## Stack

| Camada | Tecnologia |
|--------|------------|
| UI | Python 3.11 + PySide6 (Qt6) |
| PDF | PyMuPDF, pdfplumber, ReportLab |
| EPUB | ebooklib, BeautifulSoup4 |
| Tradução | deep-translator |
| Modelos | Pydantic v2 |

## Estrutura do Projeto

```
SibylaTranslate/
├── sibyla/
│   ├── core/             # Lógica de negócio (biblioteca, config, histórico, tradução)
│   ├── qt/
│   │   ├── core/         # QueueManager, sidebar_groups
│   │   ├── views/        # Telas (biblioteca, tradução, fila, histórico, config, leitor)
│   │   ├── widgets/      # BookCard, SearchBar
│   │   ├── main_window.py
│   │   └── styles.py
│   └── main.py
├── assets/               # Ícones e imagens
├── scripts/              # Scripts de build
├── run.py                # Atalho: python run.py
├── pyproject.toml
└── README.md
```

## Dados salvos no disco

| O quê | Onde |
|-------|------|
| Metadados dos livros | `~/Sibyla Library/library.json` |
| Arquivos dos livros (opcional) | `~/Sibyla Library/books/` |
| Configurações | `~/.sibyla/config.json` |
| Grupos / pastas do sidebar | `~/.sibyla/sidebar_groups.json` |
| Histórico de traduções | `~/.sibyla/config.json` → chave `historico` |

## Requisitos

- Python 3.11 ou superior
- macOS 12+ ou Windows 10/11

## Rodando Localmente

### 1. Instalar Python 3.11

**macOS (Homebrew):**
```bash
brew install python@3.11
```

**Windows:**  
Baixe em [python.org](https://www.python.org/downloads/) e marque "Add to PATH".

### 2. Criar o ambiente e instalar dependências

```bash
python3.11 -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

pip install -e .
```

### 3. Iniciar

```bash
# macOS / Linux
./dev.sh

# Windows
.\dev.ps1

# Ou diretamente
python run.py
```

## Build para Distribuição

```bash
# macOS / Linux
bash scripts/build.sh

# Windows
.\scripts\build.ps1
```

O binário gerado não requer Python instalado.

## Contribuindo

1. Faça um fork do repositório
2. Crie uma branch: `git checkout -b feature/minha-feature`
3. Faça suas alterações e teste localmente
4. Abra um Pull Request descrevendo o que mudou e por quê

### Convenções

- Estilo de código existente (sem type hints excessivos, sem comentários óbvios)
- Mensagens de commit no imperativo: `"add EPUB support"`, `"fix crash on cancel"`
- Não commitar `.venv/`, `config.json` ou arquivos gerados pelo PyInstaller

## Licença

Distribuído sob a licença MIT. Veja [LICENSE](LICENSE) para detalhes.

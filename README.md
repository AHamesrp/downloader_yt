# 🎬 Aurora YT Downloader

**Download de vídeos do YouTube sem direitos autorais**

---

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Tecnologias Utilizadas](#tecnologias-utilizadas)
- [Arquitetura do Sistema](#arquitetura-do-sistema)
- [Estrutura de Diretórios](#estrutura-de-diretórios)
- [Componentes Principais](#componentes-principais)
- [Como Funciona](#como-funciona)
- [Instalação e Configuração](#instalação-e-configuração)
- [Como Usar](#como-usar)
- [API Endpoints](#api-endpoints)
- [Dependências](#dependências)
- [Conclusão](#conclusão)

---

## 🎯 Visão Geral

Aurora YT Downloader é uma aplicação desktop moderna para download de vídeos do YouTube. O aplicativo foi desenvolvido com uma arquitetura híbrida que combina:

- **Backend**: API REST em Python com Flask
- **Frontend**: Interface web responsiva com HTML5, CSS3 e JavaScript vanilla
- **Desktop**: Integração nativa com PyWebView para uma experiência de aplicativo desktop

O sistema permite:
- ✅ Download de múltiplos vídeos do YouTube
- ✅ Extração de áudio como MP3 (com FFmpeg)
- ✅ Interface visual intuitiva e moderna
- ✅ Tracking de progresso em tempo real
- ✅ Armazenamento de URLs em localStorage
- ✅ Suporte para vídeos sem direitos autorais

---

## 🛠 Tecnologias Utilizadas

### **Backend**
| Tecnologia | Versão | Propósito |
|-----------|--------|----------|
| **Python** | 3.x | Linguagem principal |
| **Flask** | - | Framework web minimalista |
| **Flask-CORS** | - | Controle de CORS para requisições do frontend |
| **yt-dlp** | - | Download de vídeos do YouTube |
| **FFmpeg** | - | Processamento de áudio/vídeo (conversão para MP3) |
| **PyWebView** | - | Renderização de interface web em janela nativa |
| **Threading** | - | Execução assíncrona de servidores (stdlib) |
| **pathlib** | - | Manipulação de caminhos (stdlib) |
| **os** | - | Operações com sistema operacional (stdlib) |

### **Frontend**
| Tecnologia | Propósito |
|-----------|----------|
| **HTML5** | Estrutura da aplicação |
| **CSS3** | Estilização e animações (gradientes, flexbox, transições) |
| **JavaScript (Vanilla)** | Lógica do cliente sem dependências externas |
| **localStorage** | Persistência de URLs entre sessões |
| **Fetch API** | Comunicação assíncrona com o backend |
| **Google Fonts** | Tipografia (JetBrains Mono e Karla) |

### **Ferramentas de Build & Deployment**
| Ferramenta | Propósito |
|-----------|----------|
| **PyInstaller** | Empacotamento da aplicação Python em .exe |
| **Git** | Controle de versão |
| **.bat** | Scripts de inicialização no Windows |

---

## 🏗 Arquitetura do Sistema

```
┌─────────────────────────────────────────────────┐
│         APLICAÇÃO DESKTOP (PyWebView)           │
│  Janela nativa carregando http://localhost:5000 │
└────────────────┬────────────────────────────────┘
                 │
        ┌────────▼────────┐
        │  FRONTEND WEB   │
        │   (HTML/CSS/JS) │
        │  Port: n/a      │
        └────────┬────────┘
                 │ HTTP Requests
        ┌────────▼────────────────┐
        │   BACKEND FLASK API     │
        │   http://127.0.0.1:5000 │
        │                         │
        │  GET  /                 │
        │  GET  /api/progress     │
        │  POST /api/download     │
        └────────┬────────────────┘
                 │
        ┌────────▼────────────────┐
        │   YT-DLP + FFmpeg       │
        │  (Download & Conversão) │
        └────────┬────────────────┘
                 │
        ┌────────▼────────────────┐
        │  Downloads (MP4 ou MP3) │
        │  ~/Downloads/           │
        └─────────────────────────┘
```

---

## 📁 Estrutura de Diretórios

```
down/
├── app.py                          # Ponto de entrada principal (desktop)
├── app.spec                        # Configuração do PyInstaller
├── icon.ico                        # Ícone da aplicação
├── start_app.bat                   # Script para iniciar a aplicação
├── README.md                       # Este arquivo
│
├── downloader/
│   ├── server.py                   # API Flask com endpoints
│   ├── downloader.py               # Script standalone de download
│   ├── links.txt                   # Arquivo com URLs para download
│   ├── README.md                   # Documentação do módulo
│   └── __pycache__/                # Cache do Python compilado
│
├── dist/
│   ├── app.exe                     # Executável compilado
│   ├── front/
│   │   └── index.html              # Interface web (HTML/CSS/JS)
│   └── [arquivos de suporte]
│
├── build/
│   └── app/                        # Arquivos de build do PyInstaller
│       ├── Analysis-00.toc
│       ├── EXE-00.toc
│       ├── PKG-00.toc
│       ├── PYZ-00.pyz
│       ├── warn-app.txt
│       ├── xref-app.html
│       └── localpycs/
│
└── .git/                           # Repositório Git
```

---

## 🔧 Componentes Principais

### **1. `app.py` - Ponto de Entrada Desktop**

**Propósito**: Integrar Flask com PyWebView para criar uma aplicação desktop nativa.

**Fluxo de Execução**:
1. Importa Flask app do `server.py`
2. Inicia Flask em thread separada (daemon)
3. Aguarda 1 segundo para o servidor ficar pronto
4. Abre janela nativa com PyWebView apontando para `http://127.0.0.1:5000/`
5. Renderiza a interface web como um aplicativo desktop

**Configurações Importantes**:
```python
flask_app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
```
- `use_reloader=False`: Impede que PyInstaller crie processos extras
- `debug=False`: Desativa modo debug em produção
- `host="127.0.0.1"`: Apenas conexões locais (segurança)

**Código Completo**:
```python
import threading
import time
import webview  # pywebview
from downloader.server import app as flask_app

def run_flask():
    """Sobe o servidor Flask em uma thread separada."""
    flask_app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    time.sleep(1)
    window = webview.create_window("AuroraYt", "http://127.0.0.1:5000/")
    webview.start()
```

---

### **2. `downloader/server.py` - Backend API**

**Propósito**: Servir a interface web e gerenciar downloads de vídeos.

**Funcionalidades**:

#### **Endpoints**

##### `GET /`
Serve o arquivo `index.html` do frontend.
```
Resposta: HTML da aplicação web
```

##### `GET /api/progress`
Retorna o estado atual do progresso de download.
```json
{
  "status": "downloading|idle|done|error",
  "percent": 0-100,
  "current_video": "https://youtube.com/...",
  "current_video_percent": 0-100,
  "index": 1,
  "total": 5,
  "message": "Baixando vídeo 1/5"
}
```

##### `POST /api/download`
Inicia o download de múltiplos vídeos.

**Requisição**:
```json
{
  "urls": ["https://youtube.com/watch?v=...", ...],
  "audioOnly": false
}
```

**Resposta (sucesso)**:
```json
{
  "status": "ok",
  "message": "Downloads concluídos para 3 item(ns).",
  "count": 3
}
```

**Resposta (erro)**:
```json
{
  "error": "Mensagem de erro descritiva"
}
```

#### **Configurações de Download**

O sistema suporta dois modos:

1. **Vídeo + Áudio (MP4)**:
   ```python
   {
       "format": "bestvideo+bestaudio/best",
       "merge_output_format": "mp4"
   }
   ```

2. **Apenas Áudio (MP3)**:
   ```python
   {
       "format": "bestaudio/best",
       "postprocessors": [{
           "key": "FFmpegExtractAudio",
           "preferredcodec": "mp3",
           "preferredquality": "192"
       }]
   }
   ```

**Salva em**: `~/Downloads/` (pasta de downloads do Windows)

#### **Sistema de Progresso**

- Rastreia progresso por vídeo individual
- Calcula progresso geral baseado em: `(vídeos_completados + progresso_atual) / total`
- Atualiza em tempo real via hooks do yt-dlp
- Permite que o frontend faça polling a cada 1 segundo

**Principais componentes do server.py**:
- `progress_state`: Dicionário que rastreia estado do download
- `make_hook()`: Função factory que cria callbacks de progresso
- Flask app com CORS habilitado para requisições do frontend

---

### **3. `dist/front/index.html` - Interface Web**

**Propósito**: Fornecer interface visual moderna e responsiva.

#### **Seções da Interface**

1. **Header**
   - Título: "YT Downloader"
   - Subtítulo: "Download de vídeos sem direitos autorais"

2. **Área de Entrada**
   - Campo de texto para URL do YouTube
   - Botão "Adicionar"
   - Validação de URL em tempo real

3. **Fila de Downloads**
   - Lista de URLs adicionadas
   - Contador de links
   - Botão individual para remover cada link

4. **Seção de Status**
   - Mensagens de feedback (sucesso, erro, info)
   - Barra de progresso geral
   - Percentual do vídeo atual

#### **Estilo e Design**

**Paleta de Cores** (Dark Theme):
```css
:root {
    --bg-primary: #0a0e1a      /* Fundo muito escuro */
    --bg-secondary: #0f172a    /* Fundo secundário */
    --bg-tertiary: #1e293b     /* Fundo de cards */
    --accent-primary: #3b82f6  /* Azul principal */
    --accent-secondary: #60a5fa /* Azul secundário */
    --text-primary: #f1f5f9    /* Texto principal */
    --text-secondary: #94a3b8  /* Texto secundário */
    --text-tertiary: #64748b   /* Texto terciário */
}
```

**Fontes**:
- Headers: `JetBrains Mono` (monospace, display)
- Corpo: `Karla` (sans-serif legível)

**Efeitos Visuais**:
- Gradientes lineares nos títulos
- Animações de fade-in ao carregar (`fadeInUp`)
- Transições suaves em interações
- Gradientes radiais de fundo com blur
- Shadows e borders para profundidade

#### **Funcionalidades JavaScript**

1. **Gerenciamento de Links**
   - Adicionar URL (validação de YouTube com regex)
   - Remover URL individual
   - Detectar duplicatas
   - Persistir em localStorage

2. **Requisições para API**
   - POST `/api/download` para iniciar downloads
   - GET `/api/progress` para polling de progresso

3. **Polling de Progresso**
   - Intervalo: 1 segundo
   - Atualiza barra de progresso em tempo real
   - Exibe URL do vídeo atual e percentual

4. **Estado da UI**
   - Botão de download desabilitado quando lista vazia
   - Muda texto durante processamento
   - Mostra/oculta barra de progresso

5. **Armazenamento Local**
   - Salva links em `localStorage` com chave `ytDownloaderLinks`
   - Restaura links ao recarregar a página

**Exemplo de validação**:
```javascript
const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+/;
if (!youtubeRegex.test(url)) {
    showStatus('URL do YouTube inválida', 'error');
}
```

---

### **4. `downloader/downloader.py` - Script Standalone**

**Propósito**: Download direto de vídeos sem interface web (alternativa CLI).

**Como Funciona**:
1. Lê URLs do arquivo `links.txt` (um por linha)
2. Configura opções de download (melhor qualidade, legendas, etc.)
3. Download automático com `yt-dlp`
4. Salva em `downloads/` com o título do vídeo

**Configurações**:
```python
{
    'outtmpl': 'downloads/%(title)s.%(ext)s',
    'noplaylist': True,           # Não baixa playlists inteiras
    'format': 'bestvideo+bestaudio/best',
    'merge_output_format': 'mp4',
    'writesubtitles': True,       # Baixa legendas
    'subtitleslangs': ['pt', 'en'],
    'allsubtitles': True,
    'subtitles': 'auto'           # Legendas automáticas
}
```

**Uso**:
```bash
python downloader/downloader.py
```

---

## ⚙️ Como Funciona

### **Fluxo Completo de Download**

```
1. Usuário abre a aplicação (app.exe)
   ↓
2. PyWebView inicia Flask em thread daemon
   ↓
3. Interface web carrega em http://127.0.0.1:5000
   ↓
4. Usuário cola URLs do YouTube
   ↓
5. URLs são armazenadas em localStorage
   ↓
6. Usuário clica "Iniciar Download"
   ↓
7. JavaScript faz POST para /api/download
   ↓
8. Flask inicia yt-dlp para cada URL
   ↓
9. yt-dlp comunica progresso via hooks
   ↓
10. Frontend faz polling em /api/progress
   ↓
11. Barra de progresso atualiza em tempo real
   ↓
12. Vídeos são salvos em ~/Downloads/
   ↓
13. Mensagem de sucesso é exibida
```

### **Comunicação entre Componentes**

```javascript
// Frontend
fetch('http://localhost:5000/api/download', {
    method: 'POST',
    body: JSON.stringify({ urls: ["url1", "url2"] })
})

// Backend (Flask)
@app.post("/api/download")
def download_videos():
    # Processa com yt-dlp
    # Atualiza progress_state
    return jsonify(response)

// Frontend polling
setInterval(() => {
    fetch('http://localhost:5000/api/progress')
        .then(r => r.json())
        .then(data => updateProgressBar(data.percent))
}, 1000)
```

---

## 📦 Instalação e Configuração

### **Usando o Executável (app.exe)**

1. **Baixar** o executável compilado em `dist/app.exe`
2. **Executar** e pronto! (sem dependências necessárias)

Alternativa com `.bat`:
```bash
cd down/
start_app.bat
```

### **Modo Desenvolvimento**

1. **Clonar repositório**:
   ```bash
   git clone <repo-url>
   cd down
   ```

2. **Criar ambiente virtual**:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```

3. **Instalar dependências**:
   ```bash
   pip install flask flask-cors yt-dlp pywebview
   ```

   ⚠️ **FFmpeg** é necessário para conversão de áudio:
   ```bash
   # Windows (com Chocolatey)
   choco install ffmpeg
   
   # Ou baixar manualmente de https://ffmpeg.org/download.html
   ```

4. **Executar a aplicação**:
   ```bash
   python app.py
   ```

### **Compilar para Executável (PyInstaller)**

```bash
pip install pyinstaller

pyinstaller app.spec
```

O executável será gerado em `dist/app.exe`.

---

## 🚀 Como Usar

### **Via Interface Web (Recomendado)**

1. **Abra a aplicação** (desktop ou navegador)
2. **Cole uma URL do YouTube** no campo de entrada:
   ```
   https://www.youtube.com/watch?v=dQw4w9WgXcQ
   ou
   https://youtu.be/dQw4w9WgXcQ
   ```
3. **Clique "+ Adicionar"** para adicionar à fila
4. **Repita** para adicionar mais vídeos
5. **Clique "Iniciar Download"** para começar
6. **Acompanhe** o progresso em tempo real
7. **Acesse os vídeos** em `C:\Users\[seu_usuario]\Downloads\`

### **Recursos**

- ✅ **localStorage**: URLs são salvas automaticamente
- ✅ **Validação**: Apenas URLs válidas do YouTube são aceitas
- ✅ **Duplicata Check**: Não permite adicionar a mesma URL duas vezes
- ✅ **Progresso em Tempo Real**: Barra de progresso atualiza a cada segundo
- ✅ **Resposta Imediata**: Interface responsiva sem travamentos

### **Via Script CLI (downloader.py)**

1. **Edite** `downloader/links.txt` com URLs (uma por linha)
2. **Execute**:
   ```bash
   python downloader/downloader.py
   ```
3. **Vídeos são salvos** em `downloader/downloads/`

---

## 🔌 API Endpoints

### **GET** `/`
Serve a página HTML principal.

**Resposta**: `200 OK` com HTML

---

### **GET** `/api/progress`
Retorna o estado do progresso de download.

**Resposta**:
```json
{
  "status": "downloading",
  "percent": 45,
  "current_video": "https://youtube.com/watch?v=...",
  "current_video_percent": 67,
  "index": 2,
  "total": 5,
  "message": "Baixando vídeo 2/5"
}
```

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `status` | string | `idle` \| `downloading` \| `done` \| `error` |
| `percent` | int | Progresso geral (0-100) |
| `current_video` | string | URL do vídeo sendo baixado |
| `current_video_percent` | int | Progresso do vídeo atual (0-100) |
| `index` | int | Número do vídeo atual (1-based) |
| `total` | int | Total de vídeos |
| `message` | string | Mensagem descritiva |

---

### **POST** `/api/download`
Inicia o download de vídeos.

**Requisição**:
```json
{
  "urls": [
    "https://youtube.com/watch?v=...",
    "https://youtu.be/..."
  ],
  "audioOnly": false
}
```

**Query Parameters**:
| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `urls` | array | - | Lista de URLs do YouTube (obrigatório) |
| `audioOnly` | boolean | `false` | Se `true`, extrai apenas áudio como MP3 |

**Resposta (Sucesso - 200)**:
```json
{
  "status": "ok",
  "message": "Downloads concluídos para 3 item(ns).",
  "count": 3
}
```

**Resposta (Erro - 400)**:
```json
{
  "error": "Envie um JSON com o campo 'urls' como lista e pelo menos 1 URL."
}
```

**Resposta (Erro - 500)**:
```json
{
  "error": "Descrição do erro interno"
}
```

---

## 📚 Dependências

### **Python Packages**

| Pacote | Versão | Propósito |
|--------|--------|----------|
| `flask` | - | Web framework para backend |
| `flask-cors` | - | Middleware CORS para requisições cross-origin |
| `yt-dlp` | - | Download de vídeos do YouTube |
| `pywebview` | - | Integração com janela nativa do SO |

### **Ferramentas Externas**

| Ferramenta | Versão | Propósito |
|-----------|--------|----------|
| **FFmpeg** | - | Conversão de áudio/vídeo |
| **Python** | 3.7+ | Runtime |
| **Windows** | 10+ | Sistema operacional |

### **Instalação de Dependências**

```bash
pip install flask flask-cors yt-dlp pywebview
```

**FFmpeg** (necessário para MP3):
- Download: https://ffmpeg.org/download.html
- Ou via Chocolatey: `choco install ffmpeg`

---

## 📊 Estrutura de Dados

### **Progress State** (servidor)

```python
progress_state = {
    "status": "idle",              # Estado atual
    "percent": 0,                  # 0-100, progresso geral
    "current_video": None,         # URL atual ou None
    "current_video_percent": 0,    # 0-100, progresso do vídeo
    "index": 0,                    # Índice do vídeo (1-based)
    "total": 0,                    # Total de vídeos
    "message": "",                 # Mensagem para o usuário
}
```

### **Links Array** (cliente)

```javascript
let links = [
    "https://youtube.com/watch?v=ID1",
    "https://youtu.be/ID2",
    // ...
]
// Salvo em localStorage["ytDownloaderLinks"] como JSON string
```

---

## 🎨 Customização

### **Alterar Porta do Backend**

Em `app.py` e `downloader/server.py`:
```python
flask_app.run(host="127.0.0.1", port=5001)  # Exemplo: porta 5001
```

Atualizar no frontend (`index.html`):
```javascript
const API_BASE = 'http://localhost:5001';
// Se necessário em múltiplos lugares
```

### **Mudar Pasta de Downloads**

Em `downloader/server.py`:
```python
downloads_dir = "C:\\Users\\seu_usuario\\Downloads"  # ou outro caminho
```

### **Alterar Tema de Cores**

Em `index.html`, modificar as variáveis CSS:
```css
:root {
    --accent-primary: #FF6B6B;  /* Mudar cor primária */
    --bg-primary: #1A1A2E;      /* Mudar fundo */
    /* ... etc */
}
```

---

## 🐛 Troubleshooting

| Problema | Solução |
|----------|---------|
| **"FFmpeg não encontrado"** | Instalar FFmpeg e adicionar ao PATH |
| **Porta 5000 em uso** | Mudar para outra porta em `app.py` e `server.py` |
| **CORS error** | Verificar que Flask-CORS está instalado e ativo |
| **localStorage não funciona** | Usar navegador moderno (Chrome, Firefox, Edge) |
| **Vídeo não baixa** | Verificar internet, se URL é válida do YouTube |
| **Conversão MP3 falha** | Garantir FFmpeg instalado e no PATH |

---

## 📝 Logs e Debug

### **Ativar Debug Mode**

Em `downloader/server.py`:
```python
app.run(debug=True)  # Modo desenvolvimento com hot-reload
```

### **Ver Logs do YT-DLP**

Em `downloader/server.py`, adicionar:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
ydl_opts['quiet'] = False  # Mostrar logs do yt-dlp
ydl_opts['no_warnings'] = False
```

---

## 🔐 Considerações de Segurança

1. ✅ **Validação de URL**: Apenas URLs do YouTube são aceitas
2. ✅ **Localhost only**: Flask roda apenas em `127.0.0.1:5000`
3. ✅ **CORS habilitado**: Necessário para comunicação frontend-backend
4. ✅ **Sem persistência de dados sensíveis**: URLs não são salvas no servidor
5. ⚠️ **Nota legal**: Respeite direitos autorais ao fazer downloads

---

## 🚀 Melhorias Futuras

- [ ] Sistema de temas claro/escuro
- [ ] Histórico de downloads
- [ ] Suporte a playlists
- [ ] Download de legendas
- [ ] Fila persistente
- [ ] Notificações no sistema (Windows Toast)
- [ ] Conversão de formato (MP4 → MKV, etc.)
- [ ] Limite de velocidade de download
- [ ] Suporte a múltiplas abas de navegação
- [ ] Integração com VLC ou reprodutor padrão

---

## 📄 Licença

Este projeto é fornecido como está. Respecte os direitos autorais dos criadores de conteúdo do YouTube.

---

## 👨‍💻 Desenvolvimento

**Versão**: 1.0.0  
**Linguagem**: Python 3.7+  
**Status**: ✅ Funcional  
**Última atualização**: Fevereiro 2026  

---

## 📞 Contato e Suporte

Para dúvidas ou problemas, abra uma issue no repositório Git.

---

**Desenvolvido com ❤️ para download de vídeos sem direitos autorais**

# 🚀 GUIA DE USO REAL, AUTOMATIZADO E ONLINE — SPORT 5 AI

Este guia explica, passo a passo e sem termos técnicos complexos, como colocar o **SPORT 5 AI** para rodar com **raspagem real de notícias da internet**, **varredura automatizada 24h** e **acesso online** pelo navegador do celular, tablet ou computador.

---

## OPÇÃO 1: USO REAL NO SEU COMPUTADOR (1 CLIQUE)

Se você quer rodar o sistema no seu próprio computador com busca real na web:

1. **No Windows:**
   - Dê um duplo clique no arquivo `iniciar_sport5.bat`.
   - O terminal abrirá o servidor e seu navegador padrão abrirá automaticamente em `http://localhost:8000`.

2. **No Mac ou Linux:**
   - Dê um duplo clique ou execute `./iniciar_sport5.sh` no terminal.
   - O aplicativo abrirá em `http://localhost:8000`.

3. **O que acontece ao iniciar:**
   - O indicador no topo ficará: `🟢 ONLINE: Backend Conectado`.
   - O motor de busca varrerá os feeds de notícias do **Globo Esporte**, **UOL Esporte**, **Google News (Tênis de Mesa, Tênis, Futebol, etc.)** e federações oficiais.
   - A cada **15 minutos**, o robô busca novas notícias automaticamente em segundo plano, sem você precisar clicar em nada.
   - Sempre que quiser novidades na hora, clique em **[🔴 Sincronizar Feeds ao Vivo]**.

---

## OPÇÃO 2: COLOCAR ONLINE NA NUVEM GRATUITAMENTE (24H POR DIA)

Você pode hospedar o SPORT 5 AI gratuitamente em plataformas como o **Render.com** ou **Railway.app** para acessar de qualquer lugar (inclusive do celular):

### Passo a Passo no Render.com (Gratuito):
1. Crie uma conta gratuita em [https://render.com](https://render.com).
2. Crie um repositório no seu GitHub (ex: `sport5-ai`) e suba os arquivos desta pasta:
   - `server.py`
   - `sport5_ai.html`
   - `database.json`
   - `requirements.txt`
   - `Procfile`
3. No painel do Render:
   - Clique em **New +** → **Web Service**.
   - Conecte seu repositório do GitHub.
   - Em **Runtime**, selecione **Python 3**.
   - Em **Build Command**, coloque: `pip install -r requirements.txt`
   - Em **Start Command**, coloque: `python server.py`
   - Em **Instance Type**, escolha o plano **Free** (Gratuito).
4. Clique em **Create Web Service**.
5. Em 2 minutos, o Render fornecerá um link público seguro (exemplo: `https://sport5-ai.onrender.com`).
6. Pronto! Sua redação esportiva estará online 24h por dia, raspando notícias reais da web e pronta para gerar pautas, roteiros e shorts!

---

## FONTES RASTREADAS PELO MOTOR AO VIVO

O motor busca e audita automaticamente:
- ⚽ **Futebol:** Feeds oficiais do Globo Esporte, UOL e súmulas CBF/Conmebol.
- 🏀 **Basquete:** Cobertura NBA e basquete nacional (NBB/BCLA).
- 🏐 **Vôlei:** Feeds Superliga, CBV e competições internacionais.
- 🏎️ **Fórmula 1:** Feeds de esportes a motor e boletins de comissários da FIA.
- 🎾 **Tênis:** Resultados ATP Tour, WTA e Grand Slams.
- 🏓 **Tênis de Mesa (Estratégica):** Google News e canais dedicados CBTM, WTT Grand Smash e Hugo Calderano / Bruna Takahashi.

---

## CONTROLE EDITORIAL: NADA É PUBLICADO SEM SUA APROVAÇÃO
Mesmo com o motor buscando notícias na internet em tempo real:
- Toda pauta passa pelo **Fact Check 2.5** (rejeitando boatos e alucinações).
- Pautas duplicadas são unificadas com indicação do que mudou.
- O **Editor-Chefe (você)** precisa clicar em **[Aprovar]** para que o roteiro e o vídeo sejam liberados.

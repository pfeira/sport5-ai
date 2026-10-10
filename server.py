#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SPORT 5 AI — LIVE NEWSROOM & FACT CHECK ALL-IN-ONE SERVER (V2.5 / V3)
Motor Editorial e de Auditoria Factual em Tempo Real com Raspagem Contínua de Feeds.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
import threading
from datetime import datetime
from bs4 import BeautifulSoup
import http.server
import socketserver
import re
import gzip
import hashlib
from email.utils import parsedate_to_datetime
from datetime import timezone, timedelta

PORT = int(os.environ.get("PORT", 8000))
DB_FILE = "database.json"
CORRECOES_FILE = "correcoes.json"
auto_sync_interval_seconds = int(os.environ.get("SPORT5_SYNC_SECONDS", "300"))  # 5 minutos

sync_lock = threading.Lock()
last_sync_time = None
last_sync_attempt = None
last_sync_success = None
last_sync_error = None
feed_health = {}
memory_db = []

# --- CONFIGURAÇÃO DE FEEDS DE ESPORTES REAIS ---
RSS_FEEDS = [
    {
        "nome": "Google News — Esportes Brasil (Destaques)",
        "url": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdvU0FtVnVHZ0pWVXlnQVAB?hl=pt-BR&gl=BR&ceid=BR%3Apt-419",
        "padrao_esporte": "TODOS"
    },
    {
        "nome": "Google News — Futebol & Brasileirão",
        "url": "https://news.google.com/rss/search?q=futebol+brasileir%C3%A3o+OR+flamengo+OR+palmeiras+OR+corinthians&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        "padrao_esporte": "FUTEBOL"
    },
    {
        "nome": "Google News — Tênis & Masters 1000",
        "url": "https://news.google.com/rss/search?q=t%C3%AAnis+alcaraz+OR+sinner+OR+djokovic+OR+atp&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        "padrao_esporte": "TÊNIS"
    },
    {
        "nome": "Google News — Tênis de Mesa (WTT & Calderano)",
        "url": "https://news.google.com/rss/search?q=t%C3%AAnis+de+mesa+OR+calderano+OR+cbtm+OR+wtt&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        "padrao_esporte": "TÊNIS DE MESA"
    },
    {
        "nome": "Google News — Basquete & NBA",
        "url": "https://news.google.com/rss/search?q=basquete+OR+nba+OR+nbb&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        "padrao_esporte": "BASQUETE"
    },
    {
        "nome": "Google News — Fórmula 1 & Motorsport",
        "url": "https://news.google.com/rss/search?q=f%C3%B3rmula+1+OR+f1+OR+bortoleto+OR+verstappen&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        "padrao_esporte": "FÓRMULA 1"
    },
    {
        "nome": "Agência Brasil — Esportes",
        "url": "https://agenciabrasil.ebc.com.br/rss/esportes/feed.xml",
        "padrao_esporte": "TODOS"
    },
    {
        "nome": "Globo Esporte — Geral",
        "url": "https://ge.globo.com/rss/ge/",
        "padrao_esporte": "TODOS"
    },
    {
        "nome": "UOL Esporte — Ao Vivo",
        "url": "https://noticias.uol.com.br/esporte/ultimas-noticias/index.xml",
        "padrao_esporte": "TODOS"
    }
]

KEYWORD_SPORT_MAP = {
    "TÊNIS DE MESA": [
        "tênis de mesa", "mesa-tenista", "calderano", "bruna takahashi", "cbtm", 
        "wtt", "ittf", "china smash", "ping pong", "vitor ishiy", "hugo hoyama"
    ],
    "FUTEBOL": [
        "futebol", "flamengo", "palmeiras", "corinthians", "são paulo", "fluminense", 
        "botafogo", "grêmio", "internacional", "vasco", "cruzeiro", "atlético-mg", 
        "brasileirão", "libertadores", "copa do brasil", "cbf", "fifa", "champions league", 
        "premier league", "real madrid", "barcelona", "gol", "gols", "rodada", "técnico", "escalação"
    ],
    "BASQUETE": [
        "basquete", "nba", "nbb", "lakers", "celtics", "warriors", "lebron", "curry", 
        "tatum", "giannis", "fiba", "bcla", "franca basquete", "flamengo basquete", "enterro", "cesta"
    ],
    "VÔLEI": [
        "vôlei", "voleibol", "superliga", "cbv", "fivb", "seleção brasileira de vôlei", 
        "gabi guimarães", "sada cruzeiro", "praia clube", "minas tênis", "bloqueio", "levantador"
    ],
    "FÓRMULA 1": [
        "fórmula 1", "formula 1", "f1", "fia", "ferrari", "mercedes", "red bull", 
        "mclaren", "audi f1", "bortoleto", "verstappen", "hamilton", "norris", "leclerc", "gp de", "grid", "pole position"
    ],
    "TÊNIS": [
        "tênis", "tennis", "atp", "wta", "grand slam", "roland garros", "wimbledon", 
        "us open", "australian open", "alcaraz", "sinner", "djokovic", "bia haddad", 
        "masters 1000", "saibro", "tiebreak", "match point"
    ]
}

def identificar_esporte(texto, fallback="FUTEBOL"):
    texto_lower = texto.lower()
    for esporte, kws in KEYWORD_SPORT_MAP.items():
        for kw in kws:
            if kw in texto_lower:
                return esporte
    return fallback

def limpar_html(raw_html):
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator=" ").strip()


def _parse_data_publicacao(raw_date):
    """Converte datas RSS/Atom para datetime UTC; retorna None se não houver data válida."""
    if not raw_date:
        return None
    value = str(raw_date).strip()
    try:
        dt = parsedate_to_datetime(value)
        if dt:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
    except Exception:
        pass
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _local_now():
    # O Render pode rodar em UTC; o app exibe horários de Brasília.
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Sao_Paulo"))
    except Exception:
        return datetime.now()


def _normalizar_titulo(value):
    value = (value or "").lower().strip()
    value = re.sub(r"\s+-\s+[^-]+$", "", value)
    value = re.sub(r"[^a-z0-9áéíóúâêîôûãõç]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def buscar_noticias_rss():
    """Busca feeds reais, preserva a data original e descarta itens sem data/antigos."""
    global feed_health
    noticias_coletadas = []
    agora_utc = datetime.now(timezone.utc)
    janela_horas = int(os.environ.get("SPORT5_NEWS_MAX_AGE_HOURS", "48"))
    headers = {
        "User-Agent": "SPORT5AI-NewsReader/2.0 (+RSS reader; contact: sport5)",
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
        "Accept-Encoding": "gzip, deflate"
    }
    estado = {}

    for feed in RSS_FEEDS:
        nome = feed["nome"]
        info = {"url": feed["url"], "ok": False, "itens_lidos": 0,
                "itens_recentes": 0, "erro": None, "checado_em": _local_now().strftime("%d/%m/%Y %H:%M")}
        try:
            req = urllib.request.Request(feed["url"], headers=headers)
            with urllib.request.urlopen(req, timeout=6) as response:
                raw_bytes = response.read()
                encoding = (response.headers.get("Content-Encoding") or "").lower()
                if raw_bytes.startswith(b"\x1f\x8b") or encoding == "gzip":
                    try:
                        raw_bytes = gzip.decompress(raw_bytes)
                    except Exception:
                        pass

            soup = BeautifulSoup(raw_bytes, "xml")
            items = soup.find_all("item")
            if not items:
                items = soup.find_all("entry")
            info["ok"] = True
            info["itens_lidos"] = len(items)

            # RSS/Atom usually places newest first; inspect more than six.
            for item in items[:20]:
                title_el = item.find("title")
                link_el = item.find("link")
                desc_el = item.find("description") or item.find("summary") or item.find("content")
                date_el = (item.find("pubDate") or item.find("published") or
                           item.find("updated") or item.find("date"))

                title = title_el.get_text(" ", strip=True) if title_el else ""
                link = ""
                if link_el:
                    # Atom links normally store the URL in href; RSS links use text.
                    link = (link_el.get("href") or link_el.get_text(" ", strip=True) or "").strip()
                desc = limpar_html(desc_el.get_text(" ", strip=True)) if desc_el else title
                raw_pubdate = date_el.get_text(" ", strip=True) if date_el else ""
                published_dt = _parse_data_publicacao(raw_pubdate)

                if not title or len(title) < 8 or not link.startswith(("http://", "https://")):
                    continue
                if not published_dt:
                    # No inventar a data de publicação. Mantém o item fora do radar ativo.
                    continue
                age_hours = (agora_utc - published_dt).total_seconds() / 3600
                if age_hours < -2 or age_hours > janela_horas:
                    continue

                # Google News costuma acrescentar o nome do veículo ao final do título.
                if "google news" in nome.lower():
                    title = re.sub(r"\s+-\s+[^-\n]{2,80}$", "", title).strip()
                sport = identificar_esporte(title + " " + desc, feed["padrao_esporte"])
                published_local = published_dt.astimezone(_local_now().tzinfo)
                item_id = hashlib.sha1((link or _normalizar_titulo(title)).encode("utf-8")).hexdigest()[:16]
                noticias_coletadas.append({
                    "id_fonte": item_id,
                    "titulo": title,
                    "link": link,
                    "descricao": desc,
                    "data_pub": published_local.strftime("%d/%m/%Y %H:%M"),
                    "published_at_iso": published_dt.isoformat(),
                    "age_hours": round(max(0, age_hours), 1),
                    "fonte_nome": nome,
                    "esporte": sport
                })
                info["itens_recentes"] += 1
        except Exception as exc:
            info["erro"] = f"{type(exc).__name__}: {str(exc)[:180]}"
            print(f"[LIVE ENGINE] Feed falhou: {nome} — {info['erro']}", flush=True)
        estado[nome] = info

    # Deduplica por URL e por título normalizado; conserva a fonte encontrada primeiro.
    unique = []
    seen_urls, seen_titles = set(), set()
    for item in sorted(noticias_coletadas, key=lambda x: x.get("published_at_iso", ""), reverse=True):
        url_key = item["link"].split("?utm_")[0].rstrip("/")
        title_key = _normalizar_titulo(item["titulo"])
        if url_key in seen_urls or title_key in seen_titles:
            continue
        seen_urls.add(url_key)
        seen_titles.add(title_key)
        unique.append(item)

    feed_health = estado
    print(f"[LIVE ENGINE] Itens recentes e deduplicados: {len(unique)} (janela {janela_horas}h)", flush=True)
    return unique


def enriquecer_pauta(raw_noticia, index=1):
    """Cria um registro de pauta sem inventar fatos nem marcar RSS isolado como verificado."""
    now_local = _local_now()
    pub_iso = raw_noticia.get("published_at_iso")
    published = _parse_data_publicacao(pub_iso)
    published_local = published.astimezone(now_local.tzinfo) if published else None
    title = raw_noticia.get("titulo", "").strip()
    sport = raw_noticia.get("esporte", "TODOS")
    source = raw_noticia.get("fonte_nome", "Feed RSS")
    link = raw_noticia.get("link", "")
    desc = raw_noticia.get("descricao") or title
    item_id = raw_noticia.get("id_fonte") or hashlib.sha1(link.encode("utf-8")).hexdigest()[:16]
    pub_date = published_local.strftime("%d/%m/%Y") if published_local else ""
    pub_datetime = published_local.strftime("%d/%m/%Y %H:%M") if published_local else ""
    age_hours = raw_noticia.get("age_hours", 999)
    recency = "ULTIMAS_24H" if age_hours <= 24 else "ULTIMAS_48H" if age_hours <= 48 else "HISTORICO"

    return {
        "id": f"rss-{item_id}",
        "sport": sport,
        "title": title,
        "championship": f"Notícia capturada via RSS — {sport}",
        "athlete": "",
        "date": pub_date,
        "dataAconteceu": "A confirmar",
        "dataPublicado": pub_datetime,
        "dataAtualizado": now_local.strftime("%d/%m/%Y %H:%M"),
        "publishedAtISO": pub_iso,
        "firstSeenAt": now_local.isoformat(),
        "recency": recency,
        "location": "A confirmar na matéria original",
        "source": source,
        "sourceUrl": link,
        "verifiedType": "RSS_AGGREGATOR",
        "statusVerificacao": "IN_VERIFICATION",
        "statusVerificacaoLabel": "🟠 IN VERIFICATION",
        "workflowStatus": "EM_VERIFICACAO",
        "duplicidade": {"status": "ORIGINAL", "isDuplicada": False, "pautaOrigemId": None,
                        "oQueMudou": None, "quandoMudou": None, "novaFonte": None, "novaInformacao": None},
        "scoreEditorial": 50,
        "scoreEditorialBreakdown": {"relevancia": 12, "audiencia": 12, "novidade": 12,
                                    "analise": 6, "dados": 4, "visual": 4},
        "scoreConfiabilidade": 45,
        "importance": "Pauta descoberta em feed RSS. Relevância e conteúdo precisam de checagem editorial.",
        "novelty": "Capturada de feed; a data original foi preservada.",
        "stats": desc,
        "auditoriaAfirmacoes": [{
            "afirmacao": title, "fonte": source, "tipoFonte": "FEED_RSS",
            "evidencia": desc, "status": "PENDENTE_CONFIRMACAO"
        }],
        "auditoriaFontes": [{
            "nome": source, "url": link, "tipo": "FEED_RSS",
            "data": pub_date, "horario": published_local.strftime("%H:%M %Z") if published_local else "",
            "origem": "Feed RSS", "status": "CAPTURADA_NAO_VERIFICADA",
            "evidencia": desc[:300], "ultimaVerificacao": now_local.strftime("%d/%m/%Y %H:%M")
        }],
        "research": {
            "confirmados": ["O feed publicou este título na data indicada; o conteúdo ainda não foi verificado."],
            "aConfirmar": ["Confirmar o fato na matéria original.", "Buscar fonte oficial ou segunda fonte independente.",
                           "Conferir data do acontecimento, nomes, placar e estatísticas."]
        },
        "reliability": {
            "score": 45, "status": "PENDENTE", "statusLabel": "🟠 A VERIFICAR",
            "approvalStatus": "AGUARDANDO_APROVACAO", "lastChecked": now_local.strftime("%d/%m/%Y %H:%M"),
            "nextCheck": "Após checagem editorial", "contradicoes": "Ainda não verificada",
            "bloqueioProducao": True, "mensagemBloqueio": "Pauta RSS não pode virar roteiro/publicação sem confirmação."
        }
    }


def sincronizar_com_banco(db_path=DB_FILE):
    """Sincroniza só notícias recentes reais; nunca renova data de uma notícia antiga."""
    global memory_db, last_sync_time, last_sync_attempt, last_sync_success, last_sync_error
    now_local = _local_now()
    last_sync_attempt = now_local.strftime("%d/%m/%Y %H:%M:%S")
    last_sync_error = None
    existing = load_db()
    if not isinstance(existing, list):
        existing = []

    known_urls = set()
    known_titles = set()
    for item in existing:
        # Atualiza somente a classificação temporal, com base na data original real.
        # Nunca altera data de publicação nem data do acontecimento.
        if item.get("publishedAtISO"):
            published = _parse_data_publicacao(item.get("publishedAtISO"))
            if published:
                age_hours = (datetime.now(timezone.utc) - published).total_seconds() / 3600
                if age_hours <= 24:
                    item["recency"] = "ULTIMAS_24H"
                elif age_hours <= 48:
                    item["recency"] = "ULTIMAS_48H"
                else:
                    item["recency"] = "HISTORICO"
        url = (item.get("sourceUrl") or "").split("?utm_")[0].rstrip("/")
        if url.startswith(("http://", "https://")):
            known_urls.add(url)
        title = _normalizar_titulo(item.get("title", ""))
        if title:
            known_titles.add(title)

    try:
        raw_items = buscar_noticias_rss()
    except Exception as exc:
        last_sync_error = f"{type(exc).__name__}: {str(exc)[:250]}"
        print(f"[LIVE ENGINE] Sincronização falhou: {last_sync_error}", flush=True)
        return {"novas": 0, "total": len(existing), "msg": "Falha ao consultar os feeds. As pautas existentes foram preservadas.",
                "pautas": existing, "erro": last_sync_error}

    if feed_health and not any(item.get("ok") for item in feed_health.values()):
        last_sync_error = "Nenhum feed RSS respondeu com sucesso; verifique os logs e URLs das fontes."
        print(f"[LIVE ENGINE] {last_sync_error}", flush=True)
        return {"novas": 0, "total": len(existing),
                "msg": "Nenhuma fonte RSS respondeu. As notícias existentes foram preservadas sem atualizar suas datas.",
                "pautas": existing, "erro": last_sync_error, "feeds": feed_health}

    new_items = []
    for raw in raw_items:
        url_key = raw["link"].split("?utm_")[0].rstrip("/")
        title_key = _normalizar_titulo(raw["titulo"])
        if url_key in known_urls or title_key in known_titles:
            continue
        pauta = enriquecer_pauta(raw, len(new_items) + 1)
        new_items.append(pauta)
        known_urls.add(url_key)
        known_titles.add(title_key)

    if new_items:
        # Keep new RSS discoveries first; retain old items as archive, without touching their dates.
        merged = new_items + existing
        save_db(merged[:500])
        message = f"{len(new_items)} notícias recentes capturadas. Todas aguardam checagem factual."
    else:
        # Critical fix: no fake timestamp updates when feeds have no new articles.
        merged = existing
        message = "Consulta concluída; nenhum artigo novo dentro da janela de 48 horas."

    last_sync_time = now_local.strftime("%d/%m/%Y %H:%M")
    last_sync_success = last_sync_time
    print(f"[LIVE ENGINE] {message} Total no banco: {len(merged)}", flush=True)
    return {"novas": len(new_items), "total": len(merged), "msg": message, "pautas": merged,
            "feeds": feed_health, "last_sync": last_sync_time}

def load_db():
    global memory_db
    if memory_db and len(memory_db) > 0:
        return memory_db
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                memory_db = json.load(f)
                return memory_db
        except Exception as e:
            print(f"[SERVER] Erro ao ler database.json: {e}")
    return []


def marcar_base_legada_como_arquivo():
    """Dados antigos sem data original confiável não devem aparecer como notícias novas/verificadas."""
    global memory_db
    db = load_db()
    changed = False
    for pauta in db:
        if pauta.get("id", "").startswith("rss-") and pauta.get("publishedAtISO"):
            continue
        if pauta.get("recency") != "HISTORICO" or pauta.get("statusVerificacao") == "IN_VERIFICATION":
            pauta["recency"] = "HISTORICO"
            pauta["statusVerificacao"] = "IN_VERIFICATION"
            pauta["statusVerificacaoLabel"] = "🟠 ARQUIVO — DATA/FONTE A REVALIDAR"
            pauta["workflowStatus"] = "EM_VERIFICACAO"
            pauta["verifiedType"] = "LEGACY_UNVERIFIED"
            pauta["scoreConfiabilidade"] = min(int(pauta.get("scoreConfiabilidade", 45) or 45), 45)
            pauta["dataAtualizado"] = pauta.get("dataAtualizado", "")
            pauta["legacyNotice"] = "Registro herdado da base anterior. Não considerar notícia atual sem revalidação."
            changed = True
    if changed:
        save_db(db)
        print("[MIGRAÇÃO] Registros antigos sem timestamp original foram arquivados para não parecerem atuais.", flush=True)

def save_db(data):
    global memory_db
    memory_db = data
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[SERVER] Nota ao salvar em disco: {e}")

def load_correcoes():
    if os.path.exists(CORRECOES_FILE):
        try:
            with open(CORRECOES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_correcoes(data):
    try:
        with open(CORRECOES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[SERVER] Erro ao salvar correcoes.json: {e}")

def background_auto_sync():
    global last_sync_time
    print(f"[SERVER] Agendador de feeds ativo (ciclo: {auto_sync_interval_seconds // 60} min).", flush=True)
    try:
        with sync_lock:
            print("[SERVER BOOT] Executando varredura inicial nos feeds da internet...")
            res = sincronizar_com_banco(DB_FILE)
            print(f"[SERVER BOOT] Concluído: {res.get('msg')}", flush=True)
    except Exception as e:
        print(f"[SERVER BOOT] Nota na varredura inicial: {e}")

    while True:
        try:
            time.sleep(auto_sync_interval_seconds)
            with sync_lock:
                print("[SERVER AUTO-SYNC] Disparando atualização periódica dos feeds...")
                res = sincronizar_com_banco(DB_FILE)
                print(f"[SERVER AUTO-SYNC] Concluído: {res.get('msg')}", flush=True)
        except Exception as e:
            print(f"[SERVER AUTO-SYNC] Erro durante sincronização: {e}")

class Sport5APIHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        try:
            self._do_GET_impl()
        except Exception as e:
            import traceback
            print('EXCEPTION IN DO_GET:', e, traceback.format_exc(), flush=True)

    def _do_GET_impl(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/"):
            self.handle_api_get(path, urllib.parse.parse_qs(parsed.query))
        else:
            if path in ["/", "", "/index.html", "/sport5_ai.html"]:
                try:
                    db = load_db()
                    html_file = "sport5_ai.html" if os.path.exists("sport5_ai.html") else "index.html"
                    with open(html_file, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Injetar dinamicamente as pautas mais recentes em INITIAL_PAUTAS
                    pattern = r'const INITIAL_PAUTAS\s*=\s*\[.*?\];\s*(?=\s*(?:class Sport5App|const|let|var|function))'
                    replacement = 'const INITIAL_PAUTAS = ' + json.dumps(db, ensure_ascii=False) + ';'
                    content = re.sub(pattern, replacement, content, flags=re.DOTALL)

                    content_bytes = content.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Cache-Control", "no-cache, no-store, must-revalidate, max-age=0")
                    self.send_header("Pragma", "no-cache")
                    self.send_header("Expires", "0")
                    self.send_header("Content-Length", str(len(content_bytes)))
                    self.end_headers()
                    self.wfile.write(content_bytes)
                    return
                except Exception as e:
                    print(f"[SERVER] Erro ao servir HTML dinâmico: {e}", flush=True)
                    if path in ["/", "", "/index.html"]:
                        self.path = "/sport5_ai.html"
                    super().do_GET()
            else:
                super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/"):
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len) if content_len > 0 else b'{}'
            try:
                data = json.loads(post_body.decode('utf-8'))
            except Exception:
                data = {}
            self.handle_api_post(path, data)
        else:
            self.send_error(404, "Not Found")

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate, max-age=0')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_api_get(self, path, params):
        global last_sync_time
        db = load_db()

        if path == "/api/status":
            self.send_json({
                "status": "online",
                "versao": "SPORT 5 AI — RSS FIX / FACT CHECK PENDENTE",
                "total_pautas": len(db),
                "last_sync": last_sync_time,
                "last_sync_attempt": last_sync_attempt,
                "last_sync_success": last_sync_success,
                "last_sync_error": last_sync_error,
                "auto_sync_interval_min": max(1, auto_sync_interval_seconds // 60),
                "motor_scraping": "ACTIVE" if last_sync_success else "STARTING_OR_FAILED",
                "feeds": feed_health,
                "message": "O servidor está online. Notícias capturadas via RSS ficam pendentes até confirmação factual."
            })

        elif path == "/api/pautas":
            esporte = params.get("esporte", [None])[0]
            status = params.get("status", [None])[0]

            filtered = db
            if esporte and esporte != "TODOS":
                filtered = [p for p in filtered if p.get("sport") == esporte]
            if status and status != "TODOS":
                filtered = [p for p in filtered if p.get("statusVerificacao") == status]

            self.send_json({
                "status": "success",
                "count": len(filtered),
                "pautas": filtered
            })

        elif path == "/api/correcoes":
            corrs = load_correcoes()
            self.send_json({
                "status": "success",
                "count": len(corrs),
                "correcoes": corrs
            })

        elif path == "/api/export/json":
            self.send_json(db)

        elif path == "/api/export/csv":
            csv = "ID;Título;Esporte;Campeonato;Aconteceu;Publicado;Score Editorial;Score Confiabilidade;Status\n"
            for p in db:
                csv += f'"{p.get("id")}";"{p.get("title","").replace(chr(34), "")}";"{p.get("sport")}";"{p.get("championship")}";"{p.get("dataAconteceu")}";"{p.get("dataPublicado")}";{p.get("scoreEditorial")};{p.get("scoreConfiabilidade")};"{p.get("statusVerificacao")}"\n'
            self.send_response(200)
            self.send_header('Content-Type', 'text/csv; charset=utf-8')
            self.send_header('Content-Disposition', 'attachment; filename="sport5_export.csv"')
            self.end_headers()
            self.wfile.write(csv.encode('utf-8'))

        else:
            self.send_error(404, "Endpoint não encontrado")

    def handle_api_post(self, path, data):
        global last_sync_time
        db = load_db()

        if path == "/api/sync/live":
            with sync_lock:
                print("[API] Requisição de sincronização ao vivo recebida...")
                res = sincronizar_com_banco(DB_FILE)
                db_updated = load_db()
                self.send_json({
                    "status": "success" if not res.get("erro") else "partial",
                    "novas_pautas": res.get("novas", 0),
                    "total_pautas": len(db_updated),
                    "mensagem": res.get("msg"),
                    "last_sync": last_sync_time,
                    "last_sync_attempt": last_sync_attempt,
                    "erro": res.get("erro"),
                    "feeds": res.get("feeds", feed_health),
                    "pautas": db_updated
                })

        elif path == "/api/pautas/aprovar":
            pid = data.get("id")
            for p in db:
                if p["id"] == pid:
                    p["workflowStatus"] = "APROVADA"
                    save_db(db)
                    self.send_json({"status": "success", "message": "Pauta aprovada com sucesso", "pauta": p})
                    return
            self.send_json({"status": "error", "message": "Pauta não encontrada"}, 404)

        elif path == "/api/pautas/rejeitar":
            pid = data.get("id")
            for p in db:
                if p["id"] == pid:
                    p["statusVerificacao"] = "REJECTED"
                    p["workflowStatus"] = "REJEITADA"
                    save_db(db)
                    self.send_json({"status": "success", "message": "Pauta rejeitada com sucesso", "pauta": p})
                    return
            self.send_json({"status": "error", "message": "Pauta não encontrada"}, 404)

        elif path == "/api/pautas/salvar":
            pid = data.get("id")
            found = False
            for i, p in enumerate(db):
                if p["id"] == pid:
                    db[i] = data
                    found = True
                    break
            if not found:
                db.insert(0, data)
            save_db(db)
            self.send_json({"status": "success", "message": "Pauta salva com sucesso no servidor", "pauta": data})

        elif path == "/api/correcoes":
            corrs = load_correcoes()
            nova = {
                "dataHora": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "pauta": data.get("pauta", "Pauta Desconhecida"),
                "erroOriginal": data.get("erroOriginal", ""),
                "infoCorrigida": data.get("infoCorrigida", ""),
                "fonte": data.get("fonte", "Apuração Oficial"),
                "responsavel": data.get("responsavel", "Plantão SPORT 5"),
                "status": "Retificado"
            }
            corrs.insert(0, nova)
            save_correcoes(corrs)
            self.send_json({"status": "success", "message": "Correção registrada no servidor", "correcao": nova})

        else:
            self.send_error(404, "Endpoint não encontrado")

if __name__ == "__main__":
    print(f"==================================================")
    print(f"🚀 SPORT 5 AI — SERVIDOR LIVE NEWSROOM & FACT CHECK")
    print(f"==================================================")
    print(f"Endereço local: http://localhost:{PORT}")
    print(f"Interface Web: http://localhost:{PORT}/sport5_ai.html")
    print(f"API de Status:  http://localhost:{PORT}/api/status")
    print(f"API de Pautas:  http://localhost:{PORT}/api/pautas")
    print(f"Sincronização:  POST http://localhost:{PORT}/api/sync/live")
    print(f"==================================================")
    
    marcar_base_legada_como_arquivo()
    t = threading.Thread(target=background_auto_sync, daemon=True)
    t.start()

    http.server.ThreadingHTTPServer.allow_reuse_address = True
    with http.server.ThreadingHTTPServer(("", PORT), Sport5APIHandler) as httpd:
        print("HTTP SERVER LISTENING ON PORT", PORT, flush=True)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[SERVER] Servidor encerrado.")

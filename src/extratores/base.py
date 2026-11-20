"""Helpers de download com cache local."""
from __future__ import annotations

import hashlib
import json
import re
import socket
import time
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parents[2]
BRUTO = RAIZ / "dados" / "bruto"
PROCESSADO = RAIZ / "dados" / "processado"

# Cabeçalhos mensais dos anexos da STN/Tesouro: "jan/24"…"dez/24" e "2007".
# Fonte única compartilhada por tesouro.py e rmd.py (evita divergência).
MESES = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}
RE_MES = re.compile(r"^([A-Za-z]{3})/(\d{2})$")
RE_ANO = re.compile(r"^\d{4}$")


def ano_de_dois_digitos(yy: str) -> int:
    """Converte ano de 2 dígitos do cabeçalho: '99' -> 1999, '26' -> 2026.

    Usa o format %y (regra do strptime: 00-68 -> 2000-2068, 69-99 ->
    1969-1999) em vez de `2000 + yy` ingênuo, que leria o 'Jan/99' da
    aba 2.3 do anexo RMD como janeiro de 2099.

    O parse é só dos dígitos, então independe de locale — ao contrário de
    `to_datetime('Fev/99', format='%b/%y')`, que exige siglas inglesas de
    mês e falha nas 7 siglas PT diferentes (fev, abr, mai, ago, set, out,
    dez). O mês fica a cargo de MESES.

    Falha ruidosa (ValueError) se o ano resolver fora de 1990..ano
    corrente+1 — janela dos dados do projeto (RMD desde 1996; Tesouro
    desde 2000) — em vez de gravar data absurda em silêncio.
    """
    ano = int(datetime.strptime(str(yy), "%y").year)
    limite = date.today().year + 1
    if not 1990 <= ano <= limite:
        raise ValueError(
            f"ano de 2 dígitos {yy!r} resolveu para {ano}, fora da janela "
            f"1990..{limite} — cabeçalho inesperado no anexo?")
    return ano


_UA = {
    "User-Agent": "juros-e-divida/1.0 (pesquisa de transparencia publica)",
    "Accept": "application/json",
}


# Hosts como www.bcb.gov.br publicam AAAA (IPv6/Azure Front Door) mesmo em
# redes onde o IPv6 não rota: o `requests` tenta o IPv6 primeiro e estoura o
# timeout. Ordena o getaddrinfo pondo IPv4 à frente — só reordena, não força,
# então continua funcionando em rede IPv6-only. Aplicado só durante o
# download (context manager), não no import do módulo.


@contextmanager
def _ipv4_primeiro():
    original = socket.getaddrinfo

    def ordenado(host, port, *args, **kwargs):
        res = original(host, port, *args, **kwargs)
        return sorted(res, key=lambda r: 0 if r[0] == socket.AF_INET else 1)

    socket.getaddrinfo = ordenado
    try:
        yield
    finally:
        socket.getaddrinfo = original


def _cache_path(nome: str, subpasta: str) -> Path:
    d = BRUTO / subpasta
    d.mkdir(parents=True, exist_ok=True)
    return d / nome


def _destino(subpasta: str) -> Path:
    """Caminho de dados: 'bruto' fica em dados/bruto; o resto em dados/<subpasta>."""
    if subpasta == "bruto":
        BRUTO.mkdir(parents=True, exist_ok=True)
        return BRUTO
    d = RAIZ / "dados" / subpasta
    d.mkdir(parents=True, exist_ok=True)
    return d


def get(url: str, params: dict | None = None, timeout: int = 120) -> bytes:
    with _ipv4_primeiro():
        resp = requests.get(url, params=params, headers=_UA, timeout=timeout)
        resp.raise_for_status()
    return resp.content


def get_json(url: str, params: dict | None = None, timeout: int = 120, tentativas: int = 4,
             ignorar_404: bool = False):
    ultimo_erro: Exception | None = None
    for i in range(tentativas):
        try:
            with _ipv4_primeiro():
                resp = requests.get(url, params=params, headers=_UA, timeout=timeout)
            if ignorar_404 and resp.status_code == 404:
                return []  # janela sem dados (série ainda não existia)
            if resp.status_code in (429, 500, 502, 503):
                raise requests.HTTPError(f"HTTP {resp.status_code} (transiente)")
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as exc:  # inclui JSONDecodeError
            ultimo_erro = exc
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"falha após {tentativas} tentativas: {url}") from ultimo_erro


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _meta_path(dest: Path) -> Path:
    return dest.with_name(dest.name + ".meta.json")


def meta_ler(dest: Path) -> dict | None:
    """Metadados da coleta de um arquivo do cache (ou None se ausentes)."""
    p = _meta_path(dest)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except ValueError:
        return None


def meta_gravar(dest: Path, *, fonte: str, url: str,
                identificador_publicacao: str, etag: str | None = None,
                last_modified: str | None = None) -> dict:
    """Registra os metadados da coleta em <arquivo>.meta.json.

    Campos: fonte, url, data_coleta, identificador_publicacao (o que
    identifica esta versão publicada: ETag, Last-Modified ou id do anexo),
    hash_sha256 do arquivo coletado; + etag/last_modified brutos, usados
    na revalidação condicional (If-None-Match / If-Modified-Since).
    """
    meta = {
        "fonte": fonte,
        "url": url,
        "data_coleta": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "identificador_publicacao": identificador_publicacao,
        "hash_sha256": _sha256(dest),
        "etag": etag,
        "last_modified": last_modified,
    }
    _meta_path(dest).write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    return meta


def baixar_com_cache(url: str, nome: str, subpasta: str, params: dict | None = None,
                     fonte: str = "", force: bool = False) -> Path:
    """baixar(): obtém a versão ATUAL da fonte, com revalidação condicional.

    - force=False: havendo cache com metadados, revalida com If-None-Match /
      If-Modified-Since — 304 mantém a cópia local (byte-idêntica à fonte),
      200 grava a nova versão. Sem cache (ou sem metadados) -> transfere.
    - force=True: transfere de novo, ignorando a revalidação.
    - Qualquer outro status HTTP é erro claro: não cai de volta para o
      cache (falha não se disfarça de dado).

    Os metadados da coleta ficam em <arquivo>.meta.json (ver meta_gravar).
    """
    dest = _cache_path(nome, subpasta)
    meta = meta_ler(dest)
    if not force and dest.exists() and dest.stat().st_size > 0 and meta:
        headers = dict(_UA)
        if meta.get("etag"):
            headers["If-None-Match"] = meta["etag"]
        if meta.get("last_modified"):
            headers["If-Modified-Since"] = meta["last_modified"]
        with _ipv4_primeiro():
            resp = requests.get(url, params=params, headers=headers, timeout=120)
        if resp.status_code == 304:
            return dest  # nada mudou na fonte
        if resp.status_code != 200:
            raise RuntimeError(f"falha ao revalidar {url}: HTTP {resp.status_code}")
    else:
        with _ipv4_primeiro():
            resp = requests.get(url, params=params, headers=_UA, timeout=120)
        resp.raise_for_status()
        if resp.status_code == 304:
            # 304 só faz sentido com If-None-Match/If-Modified-Since;
            # aqui a requisição é incondicional — não gravar o corpo vazio
            raise RuntimeError(
                f"servidor devolveu 304 para requisição incondicional: {url}")
    dest.write_bytes(resp.content)
    time.sleep(0.3)
    meta_gravar(dest, fonte=fonte or url, url=url,
                identificador_publicacao=resp.headers.get("ETag")
                or resp.headers.get("Last-Modified") or url,
                etag=resp.headers.get("ETag"),
                last_modified=resp.headers.get("Last-Modified"))
    return dest


def usar_cache(nome: str, subpasta: str) -> Path:
    """usa_cache(): usa explicitamente a cópia local, sem consultar a fonte.

    Valida a integridade contra o hash_sha256 dos metadados: erro claro se
    o cache não existir, não tiver metadados ou estiver corrompido/trocado.
    """
    dest = _cache_path(nome, subpasta)
    if not dest.exists() or dest.stat().st_size == 0:
        raise FileNotFoundError(
            f"cache ausente: {dest} — rode baixar() para coletar da fonte")
    meta = meta_ler(dest)
    if not meta or not meta.get("hash_sha256"):
        # cópia anterior aos metadados de procedência: usa, mas rotula
        print(f"aviso: cache sem metadados ({_meta_path(dest)}) — cópia de "
              "coleta antiga, sem procedência registrada")
        return dest
    if _sha256(dest) != meta["hash_sha256"]:
        raise RuntimeError(
            f"cache corrompido/trocado: {dest} não bate com o hash_sha256 "
            "dos metadados — rode baixar(force=True)")
    return dest


def ler_cache(nome: str, subpasta: str) -> Path | None:
    p = _cache_path(nome, subpasta)
    return p if p.exists() else None


def salvar_parquet(df, nome: str, subpasta: str = "processado") -> Path:
    dest = _destino(subpasta) / (nome if nome.endswith(".parquet") else f"{nome}.parquet")
    df.to_parquet(dest, index=False)
    return dest


def ler_parquet(nome: str, subpasta: str = "processado"):
    import pandas as pd

    p = _destino(subpasta) / (nome if nome.endswith(".parquet") else f"{nome}.parquet")
    if not p.exists():
        raise FileNotFoundError(f"{p} não existe — rode o extrator correspondente.")
    return pd.read_parquet(p)


def chave(obj) -> str:
    return hashlib.md5(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:10]

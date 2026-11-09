"""Helpers de download com cache local."""
from __future__ import annotations

import hashlib
import json
import socket
import time
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parents[2]
BRUTO = RAIZ / "dados" / "bruto"
PROCESSADO = RAIZ / "dados" / "processado"

_UA = {
    "User-Agent": "juros-e-divida/1.0 (pesquisa de transparencia publica)",
    "Accept": "application/json",
}


# Hosts como www.bcb.gov.br publicam AAAA (IPv6/Azure Front Door) mesmo em
# redes onde o IPv6 não rota: o `requests` tenta o IPv6 primeiro e estoura o
# timeout. Ordena o getaddrinfo pondo IPv4 à frente — só reordena, não força,
# então continua funcionando em rede IPv6-only.
_getaddrinfo_original = socket.getaddrinfo


def _ipv4_primeiro(host, port, *args, **kwargs):
    res = _getaddrinfo_original(host, port, *args, **kwargs)
    return sorted(res, key=lambda r: 0 if r[0] == socket.AF_INET else 1)


socket.getaddrinfo = _ipv4_primeiro


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
    resp = requests.get(url, params=params, headers=_UA, timeout=timeout)
    resp.raise_for_status()
    return resp.content


def get_json(url: str, params: dict | None = None, timeout: int = 120, tentativas: int = 4,
             ignorar_404: bool = False):
    import time as _time

    ultimo_erro: Exception | None = None
    for i in range(tentativas):
        try:
            resp = requests.get(url, params=params, headers=_UA, timeout=timeout)
            if ignorar_404 and resp.status_code == 404:
                return []  # janela sem dados (série ainda não existia)
            if resp.status_code in (429, 500, 502, 503):
                raise requests.HTTPError(f"HTTP {resp.status_code} (transiente)")
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as exc:  # inclui JSONDecodeError
            ultimo_erro = exc
            _time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"falha após {tentativas} tentativas: {url}") from ultimo_erro


def baixar_com_cache(url: str, nome: str, subpasta: str, params: dict | None = None) -> Path:
    """Baixa URL e guarda cópia bruta; reusa se o arquivo já existe."""
    dest = _cache_path(nome, subpasta)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.write_bytes(get(url, params=params))
    time.sleep(0.3)
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

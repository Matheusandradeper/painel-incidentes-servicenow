"""Baixa incidentes do ServiceNow (Table API) e gera o dados_incidentes.csv.

Dois modos:
  python gerar_dados.py              -> usa os tempos REAIS (resolved_at - opened_at)
  python gerar_dados.py --sintetico  -> simula tempos de resolução e um SLA fixo de 48h
                                        (útil quando o PDI tem poucos incidentes resolvidos)

Variáveis de ambiente: SN_URL, SN_USER, SN_PASS
Opcional: SN_VERIFY_SSL=false (somente para ambientes de teste)
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd
import requests

TAMANHO_PAGINA = 500
LIMITE_MAXIMO = 5000  # trava de segurança para não baixar a instância inteira
SLA_SINTETICO_HORAS = 48

PRIORIDADES = {
    "1": "1 - Crítica",
    "2": "2 - Alta",
    "3": "3 - Moderada",
    "4": "4 - Baixa",
    "5": "5 - Planejamento",
}


def ler_configuracao():
    url = os.getenv("SN_URL")
    usuario = os.getenv("SN_USER")
    senha = os.getenv("SN_PASS")

    if not all([url, usuario, senha]):
        sys.exit("❌ Defina SN_URL, SN_USER e SN_PASS nas variáveis de ambiente.")

    verificar_ssl = os.getenv("SN_VERIFY_SSL", "true").lower() != "false"
    if not verificar_ssl:
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        print("⚠️  Verificação SSL desativada (use apenas em ambiente de teste).")

    return url.rstrip("/"), usuario, senha, verificar_ssl


def buscar_incidentes(url, usuario, senha, verificar_ssl):
    """Busca os incidentes página a página (paginação via sysparm_offset)."""
    endpoint = f"{url}/api/now/table/incident"
    registros = []
    offset = 0

    while offset < LIMITE_MAXIMO:
        params = {
            "sysparm_limit": TAMANHO_PAGINA,
            "sysparm_offset": offset,
            "sysparm_query": "ORDERBYopened_at",  # ordem estável entre páginas
            "sysparm_fields": "number,category,priority,opened_at,resolved_at,sla_due",
        }
        try:
            resposta = requests.get(
                endpoint,
                auth=(usuario, senha),
                params=params,
                headers={"Accept": "application/json"},
                verify=verificar_ssl,
                timeout=30,
            )
        except requests.RequestException as erro:
            sys.exit(f"❌ Falha de conexão com o ServiceNow: {erro}")

        if resposta.status_code != 200:
            sys.exit(f"❌ ERRO {resposta.status_code}: {resposta.text}")

        pagina = resposta.json().get("result", [])
        registros.extend(pagina)
        print(f"   página com {len(pagina)} registros (total: {len(registros)})")

        if len(pagina) < TAMANHO_PAGINA:
            break
        offset += TAMANHO_PAGINA

    return pd.DataFrame(registros)


def tratar(df, sintetico=False, seed=42):
    """Limpa os dados e calcula tempo de resolução e SLA."""
    df = df.copy()

    df["category"] = df["category"].replace("", "Não Informado")
    df["priority"] = df["priority"].map(PRIORIDADES).fillna("Não Informado")

    for coluna in ["opened_at", "resolved_at", "sla_due"]:
        df[coluna] = pd.to_datetime(df[coluna], errors="coerce")

    if sintetico:
        rng = np.random.default_rng(seed)
        resolvido = df["resolved_at"].notna().to_numpy()
        lento = rng.random(len(df)) < 0.2  # ~20% dos casos demoram mais
        horas = np.where(
            lento,
            rng.integers(72, 120, len(df)),
            rng.integers(1, 72, len(df)),
        )
        df["tempo_resolucao_horas"] = np.where(resolvido, horas, np.nan)
        df["resolved_at"] = df["opened_at"] + pd.to_timedelta(
            df["tempo_resolucao_horas"], unit="h"
        )
        df["sla_due"] = df["opened_at"] + pd.Timedelta(hours=SLA_SINTETICO_HORAS)
    else:
        df["tempo_resolucao_horas"] = (
            (df["resolved_at"] - df["opened_at"]).dt.total_seconds() / 3600
        ).round(1)

    df["sintetico"] = sintetico

    return df[
        [
            "number",
            "category",
            "priority",
            "opened_at",
            "resolved_at",
            "sla_due",
            "tempo_resolucao_horas",
            "sintetico",
        ]
    ]


def main():
    parser = argparse.ArgumentParser(description="Gera dados_incidentes.csv a partir do ServiceNow")
    parser.add_argument(
        "--sintetico",
        action="store_true",
        help="simula tempos de resolução e SLA de 48h em vez de usar os dados reais",
    )
    args = parser.parse_args()

    url, usuario, senha, verificar_ssl = ler_configuracao()

    print("Buscando dados do ServiceNow...")
    bruto = buscar_incidentes(url, usuario, senha, verificar_ssl)
    if bruto.empty:
        sys.exit("❌ Nenhum incidente retornado.")
    print(f"✅ {len(bruto)} incidentes baixados!")

    df = tratar(bruto, sintetico=args.sintetico)
    df.to_csv("dados_incidentes.csv", index=False)

    modo = "SINTÉTICOS" if args.sintetico else "REAIS"
    print(f"✅ 'dados_incidentes.csv' gerado (tempos {modo}).")


if __name__ == "__main__":
    main()
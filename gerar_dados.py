import requests
import urllib3
import os
import pandas as pd
import numpy as np
from datetime import timedelta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url_base = os.getenv("SN_URL")
usuario = os.getenv("SN_USER")
senha = os.getenv("SN_PASS")

endpoint = f"{url_base}/api/now/table/incident"

params = {
    "sysparm_limit": 500,
    "sysparm_fields": "number,category,opened_at,resolved_at",
}

print("Buscando dados do ServiceNow...")
resposta = requests.get(endpoint, auth=(usuario, senha), params=params, headers={"Accept": "application/json"}, verify=False)

if resposta.status_code == 200:
    df = pd.DataFrame(resposta.json().get("result", []))
    print(f"✅ {len(df)} incidentes baixados!")

    # 1. Limpando categoria vazia
    df['category'] = df['category'].replace('', 'Não Informado')

    # 2. Convertendo datas
    df['opened_at'] = pd.to_datetime(df['opened_at'])
    df['resolved_at'] = pd.to_datetime(df['resolved_at'])

    # 3. Criando tempos de resolução realistas (entre 1 e 72 horas, com alguns picos)
    tempos_resolucao_horas = []
    
    for index, row in df.iterrows():
        if pd.isna(row['resolved_at']):
            tempos_resolucao_horas.append(None) 
        else:
            if np.random.rand() < 0.2: # 20% dos casos demoram mais
                horas = np.random.randint(72, 120)
            else:
                horas = np.random.randint(1, 72)
            tempos_resolucao_horas.append(horas)

    df['tempo_resolucao_horas'] = tempos_resolucao_horas

    # 4. Recalculando a data de resolução e criando o SLA de 48h
    df['resolved_at'] = df.apply(
        lambda row: row['opened_at'] + timedelta(hours=row['tempo_resolucao_horas']) 
        if pd.notna(row['tempo_resolucao_horas']) else pd.NaT, 
        axis=1
    )
    
    df['sla_due'] = df['opened_at'] + timedelta(hours=48)

    df = df[['number', 'category', 'opened_at', 'resolved_at', 'sla_due', 'tempo_resolucao_horas']]

    # Salva o arquivo
    df.to_csv('dados_incidentes.csv', index=False)
    print("✅ Arquivo 'dados_incidentes.csv' gerado com sucesso!")

else:
    print(f"❌ ERRO {resposta.status_code}: {resposta.text}")
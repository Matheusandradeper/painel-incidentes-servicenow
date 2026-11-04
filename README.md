# 📊 Painel de Incidentes - ServiceNow

Um dashboard interativo construído em Python para análise de chamados de TI, integrado à API REST do ServiceNow.

## 🚀 Funcionalidades
- Conexão via API REST com instâncias do ServiceNow.
- Tratamento de dados (limpeza de datas e categorias).
- Cálculo de MTTR (Mean Time To Resolution).
- Cálculo de cumprimento de SLA.
- Interface interativa com Streamlit.

## 🛠️ Tecnologias Utilizadas
- Python 3
- Streamlit (Interface)
- Pandas (Análise de dados)
- Requests (Requisições HTTP)

## ⚙️ Como rodar o projeto localmente
1. Clone o repositório.
2. Crie um ambiente virtual: `python -m venv .venv`
3. Ative o ambiente: `.venv\Scripts\Activate.ps1` (Windows)
4. Instale as dependências: `pip install -r requirements.txt`
5. Gere os dados (necessário ter credenciais do ServiceNow nas variáveis de ambiente):
   `python gerar_dados.py`
6. Rode o painel: `streamlit run app.py`
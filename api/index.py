from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# Sua chave da Rainforest API
API_KEY = "E26F264275FD4B31B4D33F1646CC3889"

def buscar_preco_rainforest(livro, dominio):
    # Parâmetros oficiais da documentação da Rainforest
    params = {
        'api_key': API_KEY,
        'type': 'search',
        'amazon_domain': dominio,
        'search_term': f"{livro} kindle", # Força a busca pela versão digital
        'sort_by': 'relevance'
    }
    
    try:
        resposta = requests.get('https://api.rainforestapi.com/request', params=params)
        dados = resposta.json()
        
        # Pega o primeiro resultado da busca
        if 'search_results' in dados and len(dados['search_results']) > 0:
            resultado = dados['search_results'][0]
            # Verifica se o item tem um preço listado
            if 'price' in resultado:
                return resultado['price']['value']
        return None
    except Exception as e:
        return None

@app.route('/api/comparar', methods=['GET'])
def comparar():
    livro = request.args.get('livro')
    
    if not livro:
        return jsonify({"erro": "Nome do livro não fornecido"}), 400

    # 1. Busca a cotação real e atualizada do dólar
    try:
        url_moeda = "https://api.exchangerate-api.com/v4/latest/USD"
        resposta_moeda = requests.get(url_moeda)
        cotacao = resposta_moeda.json()['rates']['BRL']
    except:
        cotacao = 5.00 # Valor de segurança caso a API de moeda falhe

    # 2. Busca os preços reais na Amazon via Rainforest API
    preco_br = buscar_preco_rainforest(livro, 'amazon.com.br')
    preco_us_dolar = buscar_preco_rainforest(livro, 'amazon.com')
    
    # Validação caso não encontre o livro em alguma das lojas
    if preco_br is None or preco_us_dolar is None:
        return jsonify({"erro": "Preço não encontrado. Tente digitar o nome mais completo do livro."}), 404
    
    # 3. Faz a matemática (adicionando ~5% de IOF/Spread para compras internacionais)
    preco_us_convertido = (preco_us_dolar * cotacao) * 1.05
    mais_barato = "Brasil" if preco_br <= preco_us_convertido else "EUA"
    
    return jsonify({
        "livro": livro,
        "preco_brasil_brl": round(preco_br, 2),
        "preco_eua_usd": round(preco_us_dolar, 2),
        "preco_eua_convertido_brl": round(preco_us_convertido, 2),
        "cotacao_usada": round(cotacao, 2),
        "mais_viavel": mais_barato
    })
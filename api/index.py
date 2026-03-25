from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

API_KEY = "E26F264275FD4B31B4D33F1646CC3889"

# Rota 1: Traz a lista de livros e capas
@app.route('/api/buscar', methods=['GET'])
def buscar_livros():
    termo = request.args.get('q')
    if not termo:
        return jsonify({"erro": "Termo não fornecido"}), 400

    params = {
        'api_key': API_KEY,
        'type': 'search',
        'amazon_domain': 'amazon.com.br',
        'search_term': f"{termo} kindle",
        'sort_by': 'relevance'
    }
    
    try:
        resposta = requests.get('https://api.rainforestapi.com/request', params=params)
        dados = resposta.json()
        
        resultados = []
        # Pega os 6 primeiros resultados válidos
        if 'search_results' in dados:
            for item in dados['search_results'][:6]:
                if 'asin' in item and 'title' in item:
                    resultados.append({
                        'titulo': item['title'],
                        'imagem': item.get('image', ''), # Pega a URL da capa
                        'asin': item['asin']
                    })
        return jsonify(resultados)
    except Exception as e:
        return jsonify({"erro": "Falha ao buscar os livros."}), 500

# Função auxiliar para buscar o preço do produto exato (pelo ASIN)
def buscar_preco_por_asin(asin, dominio):
    params = {
        'api_key': API_KEY,
        'type': 'product',
        'amazon_domain': dominio,
        'asin': asin
    }
    try:
        dados = requests.get('https://api.rainforestapi.com/request', params=params).json()
        if 'product' in dados and 'buybox_winner' in dados['product']:
            if 'price' in dados['product']['buybox_winner']:
                return dados['product']['buybox_winner']['price']['value']
        return None
    except: return None

# Rota 2: Compara os preços do livro selecionado
@app.route('/api/comparar', methods=['GET'])
def comparar():
    asin = request.args.get('asin')
    titulo = request.args.get('titulo', 'Livro Selecionado')
    
    if not asin:
        return jsonify({"erro": "ASIN não fornecido"}), 400

    # 1. Cotação
    try:
        cotacao = requests.get("https://api.exchangerate-api.com/v4/latest/USD").json()['rates']['BRL']
    except:
        cotacao = 5.00

    # 2. Busca preços exatos
    preco_br = buscar_preco_por_asin(asin, 'amazon.com.br')
    preco_us_dolar = buscar_preco_por_asin(asin, 'amazon.com')
    
    if preco_br is None or preco_us_dolar is None:
        return jsonify({"erro": "Não foi possível encontrar o preço digital nas duas lojas."})
    
    # 3. Matemática
    preco_us_convertido = (preco_us_dolar * cotacao) * 1.05
    mais_barato = "Brasil" if preco_br <= preco_us_convertido else "EUA"
    
    return jsonify({
        "livro": titulo,
        "preco_brasil_brl": round(preco_br, 2),
        "preco_eua_usd": round(preco_us_dolar, 2),
        "preco_eua_convertido_brl": round(preco_us_convertido, 2),
        "cotacao_usada": round(cotacao, 2),
        "mais_viavel": mais_barato
    })
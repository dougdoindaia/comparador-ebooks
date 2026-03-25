from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# Sua chave da Rainforest API
API_KEY = "E26F264275FD4B31B4D33F1646CC3889"

# Rota 1: Traz a lista de livros e capas
@app.route('/api/buscar', methods=['GET'])
def buscar_livros():
    termo = request.args.get('q')
    if not termo:
        return jsonify({"erro": "Termo não fornecido"}), 400

    # Removido o 'sort_by': 'relevance' que estava causando o bloqueio
    params = {
        'api_key': API_KEY,
        'type': 'search',
        'amazon_domain': 'amazon.com.br',
        'search_term': f"{termo} kindle"
    }
    
    try:
        resposta = requests.get('https://api.rainforestapi.com/request', params=params)
        dados = resposta.json()
        
        # MODO DETETIVE: Verifica se a Rainforest bloqueou
        if 'request_info' in dados and dados['request_info'].get('success') == False:
            mensagem = dados['request_info'].get('message', 'Erro desconhecido na API')
            return jsonify({"erro": f"Rainforest recusou: {mensagem}"})

        resultados = []
        if 'search_results' in dados:
            for item in dados['search_results'][:6]: # Pega os 6 primeiros
                if 'asin' in item and 'title' in item:
                    resultados.append({
                        'titulo': item['title'],
                        'imagem': item.get('image', ''), 
                        'asin': item['asin']
                    })
            
            # Se achou produtos, mas nenhum tinha o código ASIN
            if len(resultados) == 0:
                return jsonify({"erro": "A Amazon retornou produtos, mas nenhum possuía o código ASIN."})
                
            return jsonify(resultados)
        else:
            return jsonify({"erro": "A API não devolveu a lista de resultados (search_results ausente)."})
            
    except Exception as e:
        return jsonify({"erro": f"Falha no servidor Python: {str(e)}"}), 500

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
        
        # Tenta pegar o preço do quadro principal (buybox)
        if 'product' in dados and 'buybox_winner' in dados['product']:
            if 'price' in dados['product']['buybox_winner']:
                return dados['product']['buybox_winner']['price']['value']
                
        # Fallback: tenta pegar o preço base alternativo caso o buybox não exista
        if 'product' in dados and 'price' in dados['product']:
            return dados['product']['price'].get('value')
            
        return None
    except: 
        return None

# Rota 2: Compara os preços do livro selecionado
@app.route('/api/comparar', methods=['GET'])
def comparar():
    asin = request.args.get('asin')
    titulo = request.args.get('titulo', 'Livro Selecionado')
    
    if not asin:
        return jsonify({"erro": "ASIN não fornecido"}), 400

    # 1. Cotação do Dólar
    try:
        url_moeda = "https://api.exchangerate-api.com/v4/latest/USD"
        resposta_moeda = requests.get(url_moeda)
        cotacao = resposta_moeda.json()['rates']['BRL']
    except:
        cotacao = 5.00 # Valor de segurança

    # 2. Busca preços exatos nas duas lojas
    preco_br = buscar_preco_por_asin(asin, 'amazon.com.br')
    preco_us_dolar = buscar_preco_por_asin(asin, 'amazon.com')
    
    if preco_br is None or preco_us_dolar is None:
        return jsonify({"erro": "Não foi possível encontrar o preço da versão digital nas duas lojas para este ASIN."})
    
    # 3. Matemática (adicionando ~5% de taxas para compra internacional)
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
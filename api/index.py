from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
# O CORS permite que o seu index.html acesse essa API sem ser bloqueado pelo navegador
CORS(app)

@app.route('/api/comparar', methods=['GET'])
def comparar():
    livro = request.args.get('livro')
    
    if not livro:
        return jsonify({"erro": "Nome do livro não fornecido"}), 400

    # 1. Busca a cotação real do dólar
    try:
        url_moeda = "https://api.exchangerate-api.com/v4/latest/USD"
        resposta_moeda = requests.get(url_moeda)
        cotacao = resposta_moeda.json()['rates']['BRL']
    except:
        cotacao = 5.00 # Valor de segurança caso a API de moeda falhe

    # 2. Busca na Amazon (AQUI FICA O DESAFIO)
    # Como não podemos usar o Playwright aqui, o ideal para um projeto real 
    # é usar uma API de scraping gratuita (como a Rainforest API).
    # Por enquanto, vou colocar valores simulados para você ver a comunicação 
    # entre seu HTML e a Vercel funcionando na prática:
    
    preco_br = 39.90 
    preco_us_dolar = 5.99 
    
    # 3. Faz a matemática
    preco_us_convertido = preco_us_dolar * cotacao
    mais_barato = "Brasil" if preco_br < preco_us_convertido else "EUA"
    
    return jsonify({
        "livro": livro,
        "preco_brasil_brl": round(preco_br, 2),
        "preco_eua_usd": round(preco_us_dolar, 2),
        "preco_eua_convertido_brl": round(preco_us_convertido, 2),
        "cotacao_usada": cotacao,
        "mais_viavel": mais_barato
    })
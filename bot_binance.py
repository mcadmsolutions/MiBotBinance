import os
import time
import threading
from datetime import datetime
import pandas as pd
from binance.client import Client
from binance.enums import *
from dotenv import load_dotenv
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from flask import Flask, jsonify

# Carga de variables de entorno
load_dotenv()
api_key = os.getenv("API_KEY")
secret_key = os.getenv("SECRET_KEY")

# Cliente Binance
client = Client(api_key, secret_key, testnet=True)

# Parámetros del bot
PARAMS = {
    'symbol': 'BTCUSDT',
    'timeframe': KLINE_INTERVAL_15MINUTE,
    'ema_short': 9,
    'ema_long': 21,
    'rsi_window': 14,
    'rsi_umbral': 45,
    'take_profit': 1.5,
    'stop_loss': 0.75,
    'quantity': 0.001,
    'sleep_time': 60
}

# App Flask
app = Flask(__name__)

@app.route('/')
def health_check():
    return jsonify({
        "status": "running",
        "last_check": get_current_time(),
        "service": "binance-bot"
    }), 200

@app.route('/favicon.ico')
def favicon():
    return '', 204

def get_current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def calcular_indicadores():
    klines = client.get_historical_klines(
        symbol=PARAMS['symbol'],
        interval=PARAMS['timeframe'],
        start_str="24 hours ago UTC"
    )
    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base', 'taker_buy_quote', 'ignore'
    ])
    df['close'] = pd.to_numeric(df['close'])
    df['high'] = pd.to_numeric(df['high'])

    df['ema9'] = EMAIndicator(df['close'], window=PARAMS['ema_short']).ema_indicator()
    df['ema21'] = EMAIndicator(df['close'], window=PARAMS['ema_long']).ema_indicator()
    df['rsi'] = RSIIndicator(df['close'], window=PARAMS['rsi_window']).rsi()

    return df.iloc[-1]

def ejecutar_estrategia():
    try:
        print(f"[{get_current_time()}] 📈 Ejecutando estrategia...", flush=True)
        precio_actual = float(client.get_symbol_ticker(symbol=PARAMS['symbol'])['price'])
        indicadores = calcular_indicadores()

        ema_cond = indicadores['ema9'] > indicadores['ema21']
        rsi_cond = indicadores['rsi'] < PARAMS['rsi_umbral']
        price_cond = precio_actual > indicadores['high']

        if ema_cond and rsi_cond and price_cond:
            print(f"[{get_current_time()}] 🟢 COMPRA | Precio: {precio_actual:.2f} | RSI: {indicadores['rsi']:.2f}", flush=True)

            order = client.create_order(
                symbol=PARAMS['symbol'],
                side=Client.SIDE_BUY,
                type=Client.ORDER_TYPE_MARKET,
                quantity=PARAMS['quantity']
            )
            print(f"[{get_current_time()}] ✅ Orden ejecutada: ID {order['orderId']}", flush=True)

            take_profit = round(precio_actual * (1 + PARAMS['take_profit'] / 100), 2)
            stop_loss = round(precio_actual * (1 - PARAMS['stop_loss'] / 100), 2)

            oco_order = client.create_oco_order(
                symbol=PARAMS['symbol'],
                side=Client.SIDE_SELL,
                quantity=PARAMS['quantity'],
                stopPrice=stop_loss,
                stopLimitPrice=stop_loss,
                price=take_profit
            )
            print(f"[{get_current_time()}] 🔷 OCO Configurado | TP: {take_profit} | SL: {stop_loss}", flush=True)
        else:
            print(f"[{get_current_time()}] 🔴 Sin señal | EMA9: {indicadores['ema9']:.2f} > EMA21: {indicadores['ema21']:.2f} = {ema_cond} | "
                  f"RSI: {indicadores['rsi']:.2f} < {PARAMS['rsi_umbral']} = {rsi_cond} | "
                  f"Precio actual: {precio_actual:.2f} > High: {indicadores['high']:.2f} = {price_cond}", flush=True)

    except Exception as e:
        print(f"[{get_current_time()}] ❌ Error: {str(e)}", flush=True)

def run_bot():
    print(f"[{get_current_time()}] 🚀 Iniciando bot con timeframe: {PARAMS['timeframe']}", flush=True)
    while True:
        ejecutar_estrategia()
        time.sleep(PARAMS['sleep_time'])

# Llamado desde start.py
def iniciar_bot():
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()

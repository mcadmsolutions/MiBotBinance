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

# --- Cargar API keys --- #
load_dotenv()
api_key = os.getenv("API_KEY")
secret_key = os.getenv("SECRET_KEY")
client = Client(api_key, secret_key, testnet=True)

# --- Parámetros del bot --- #
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

# --- Flask app --- #
app = Flask(__name__)

@app.route('/')
def status():
    return jsonify({
        'status': 'Bot activo',
        'hora': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }), 200

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
        ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{ahora}] Ejecutando estrategia...", flush=True)

        precio = float(client.get_symbol_ticker(symbol=PARAMS['symbol'])['price'])
        ind = calcular_indicadores()

        ema_ok = ind['ema9'] > ind['ema21']
        rsi_ok = ind['rsi'] < PARAMS['rsi_umbral']
        precio_ok = precio > ind['high']

        if ema_ok and rsi_ok and precio_ok:
            print(f"[{ahora}] 🟢 COMPRA | Precio: {precio:.2f} | RSI: {ind['rsi']:.2f}", flush=True)

            order = client.create_order(
                symbol=PARAMS['symbol'],
                side=Client.SIDE_BUY,
                type=Client.ORDER_TYPE_MARKET,
                quantity=PARAMS['quantity']
            )
            print(f"[{ahora}] ✅ Orden ejecutada ID: {order['orderId']}", flush=True)

            tp = round(precio * (1 + PARAMS['take_profit'] / 100), 2)
            sl = round(precio * (1 - PARAMS['stop_loss'] / 100), 2)

            client.create_oco_order(
                symbol=PARAMS['symbol'],
                side=Client.SIDE_SELL,
                quantity=PARAMS['quantity'],
                stopPrice=sl,
                stopLimitPrice=sl,
                price=tp
            )
            print(f"[{ahora}] 🔷 OCO configurado | TP: {tp} | SL: {sl}", flush=True)
        else:
            print(f"[{ahora}] 🔴 Sin señal | EMA9: {ind['ema9']:.2f} > EMA21: {ind['ema21']:.2f}={ema_ok} | "
                  f"RSI: {ind['rsi']:.2f}<{PARAMS['rsi_umbral']}={rsi_ok} | "
                  f"Precio: {precio:.2f}>{ind['high']:.2f}={precio_ok}", flush=True)

    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Error: {e}", flush=True)

def run_bot():
    while True:
        ejecutar_estrategia()
        time.sleep(PARAMS['sleep_time'])

# --- Lanzar Flask + Bot --- #
if __name__ == '__main__':
    # Iniciar el bot en segundo plano
    threading.Thread(target=run_bot, daemon=True).start()

    # Ejecutar servidor Flask
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

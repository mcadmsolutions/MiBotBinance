web: gunicorn bot_binance:app
web: python bot_binance.py
web: gunicorn -b 0.0.0.0:$PORT app:app --log-file=- --access-logfile=-

from app import app, iniciar_bot

# Inicia el hilo del bot
iniciar_bot()

# Esto es lo que gunicorn buscará como punto de entrada
application = app

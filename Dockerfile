# Imagen base oficial de Python
FROM python:3.10-slim

# Establecer directorio de trabajo
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar archivos al contenedor
COPY . .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Exponer el puerto que usará Flask/Gunicorn
EXPOSE 8080

# Comando para ejecutar Gunicorn y servir Flask
CMD ["gunicorn", "-b", "0.0.0.0:8080", "bot_binance:app"]

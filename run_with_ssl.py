import os
import ssl
from simple_bot import app

if __name__ == '__main__':
    # Генерируем самоподписанный сертификат (для тестирования)
    os.system('openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365 -subj "/CN=localhost"')
    
    # Запускаем Flask с SSL
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('cert.pem', 'key.pem')
    
    app.run(host='0.0.0.0', port=5000, ssl_context=context) 
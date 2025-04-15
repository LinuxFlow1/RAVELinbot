import sys
path = '/home/linuxflow/RAVELinbot'
if path not in sys.path:
    sys.path.append(path)

from pythonanywhere_flask_app import application 
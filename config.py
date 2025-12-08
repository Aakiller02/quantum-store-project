import os
from dotenv import load_dotenv

load_dotenv()

MYSQL_HOST = 'localhost'
MYSQL_USER = 'root'
MYSQL_PASSWORD = ''
MYSQL_DB = 'Quantum'
MYSQL_CURSORCLASS = 'DictCursor'
SECRET_KEY = os.getenv('SECRET_KEY')
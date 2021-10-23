import os
from dotenv import load_dotenv

load_dotenv()

RANDOM_KEY = os.getenv('SECRET_KEY')
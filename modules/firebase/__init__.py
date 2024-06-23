import firebase_admin
from firebase_admin import credentials

from config import FIREBASE_TOKEN

cred = credentials.Certificate(FIREBASE_TOKEN)
firebase_app = firebase_admin.initialize_app(cred)

import mysql.connector

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Y@0463rn", 
    "database": "campus_club_db"
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'flood_victim_system.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Admin table
    c.execute('''
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')
    # Victims table (including optional latitude/longitude for mapping)
    c.execute('''
        CREATE TABLE IF NOT EXISTS victims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            contact_number TEXT,
            address TEXT,
            district TEXT,
            last_known_location TEXT,
            latitude TEXT,
            longitude TEXT,
            medical_conditions TEXT,
            emergency_status TEXT,
            photo_path TEXT,
            rescue_status TEXT DEFAULT 'Pending'
        )
    ''')
    # Missing persons table (including optional coordinates)
    c.execute('''
        CREATE TABLE IF NOT EXISTS missing_persons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            photo_path TEXT,
            last_seen_location TEXT,
            latitude TEXT,
            longitude TEXT,
            date_reported TEXT,
            contact_details TEXT
        )
    ''')
    # Identification results table
    c.execute('''
        CREATE TABLE IF NOT EXISTS identification_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            victim_photo_path TEXT,
            missing_person_id INTEGER,
            confidence REAL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(missing_person_id) REFERENCES missing_persons(id)
        )
    ''')
    # Rescue teams table (simplified)
    c.execute('''
        CREATE TABLE IF NOT EXISTS rescue_teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact_number TEXT
        )
    ''')
    # Rescue records linking victims to teams
    c.execute('''
        CREATE TABLE IF NOT EXISTS rescue_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            victim_id INTEGER,
            team_id INTEGER,
            status TEXT,
            notes TEXT,
            FOREIGN KEY(victim_id) REFERENCES victims(id),
            FOREIGN KEY(team_id) REFERENCES rescue_teams(id)
        )
    ''')
    # Insert a default admin if none exists
    c.execute("SELECT COUNT(*) FROM admin")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO admin (username, password) VALUES (?, ?)", ('admin', 'admin'))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print('Database initialized.')


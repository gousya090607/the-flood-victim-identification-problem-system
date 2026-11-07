import os
from PIL import Image
import imagehash
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), 'flood_victim_system.db')

def get_missing_persons():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute('SELECT * FROM missing_persons').fetchall()
    conn.close()
    return rows

def compute_hash(image_path):
    try:
        img = Image.open(image_path).convert('RGB')
        return imagehash.average_hash(img)
    except Exception as e:
        return None

def find_similar_missing(victim_image_path, threshold=10):
    """Return a list of dicts with missing person info and confidence.
    Confidence is computed as a simple inverse of Hamming distance.
    """
    victim_hash = compute_hash(victim_image_path)
    if victim_hash is None:
        return []
    results = []
    for person in get_missing_persons():
        if not person['photo_path']:
            continue
        missing_path = os.path.join('static', 'uploads', person['photo_path'])
        missing_hash = compute_hash(missing_path)
        if missing_hash is None:
            continue
        distance = victim_hash - missing_hash  # Hamming distance
        if distance <= threshold:
            confidence = max(0, (threshold - distance) / threshold) * 100
            results.append({
                'id': person['id'],
                'full_name': person['full_name'],
                'age': person['age'],
                'gender': person['gender'],
                'photo_path': person['photo_path'],
                'confidence': round(confidence, 2)
            })
    # Sort by confidence descending
    results.sort(key=lambda x: x['confidence'], reverse=True)
    return results


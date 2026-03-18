from flask import Flask, request, render_template_string, jsonify
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

def get_db():
    """Connect to PostgreSQL database using environment variables"""
    return psycopg2.connect(
        dbname=os.getenv('DB_NAME', 'toothsnap_db'),
        user=os.getenv('DB_USER', 'sim_admin'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432')
    )

@app.route('/')
def home():
    """Serve the main landing page"""
    with open('index.html') as f:
        return f.read()

@app.route('/search')
def search():
    """Search for dentists by city, state, and insurance"""
    city = request.args.get('city', '')
    state = request.args.get('state', '')
    insurance = request.args.get('insurance', '')
    
    conn = get_db()
    cur = conn.cursor()
    
    # Build dynamic query based on search parameters
    query = """
        SELECT DISTINCT d.id, d.name, d.practice_name, d.address, d.city, d.state, d.zip, d.phone, d.rating
        FROM dentists d
        LEFT JOIN dentist_insurance di ON d.id = di.dentist_id
        WHERE 1=1
    """
    params = []
    
    if city:
        query += " AND d.city ILIKE %s"
        params.append(f"%{city}%")
        
    if state:
        query += " AND d.state = %s"
        params.append(state)
        
    if insurance:
        query += " AND di.provider_id = %s"
        params.append(int(insurance))
        
    # Sort by rating if search criteria provided, otherwise alphabetically
    if not city and not state and not insurance:
        query += " ORDER BY d.practice_name ASC"
    else:
        query += " ORDER BY d.rating DESC"
    
    cur.execute(query, params)
    results = cur.fetchall()
    
    # Get insurance providers for each dentist
    dentists = []
    for row in results:
        cur.execute('''
            SELECT ip.name 
            FROM insurance_providers ip
            JOIN dentist_insurance di ON ip.id = di.provider_id
            WHERE di.dentist_id = %s
        ''', (row[0],))
        insurance_list = [r[0] for r in cur.fetchall()]
        
        dentists.append({
            'id': row[0],
            'name': row[1],
            'practice_name': row[2],
            'address': row[3],
            'city': row[4],
            'state': row[5],
            'zip': row[6],
            'phone': row[7],
            'rating': float(row[8]) if row[8] else 0,
            'insurance': ', '.join(insurance_list)
        })
    
    cur.close()
    conn.close()
    
    # Render results page
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>ToothSnap - Search Results</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { text-align: center; color: white; margin-bottom: 40px; }
            .header h1 { font-size: 2.5em; margin-bottom: 10px; }
            .results-count { color: white; font-size: 1.2em; margin-bottom: 20px; }
            .dentist-card { background: white; border-radius: 15px; padding: 30px; margin-bottom: 20px; box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
            .dentist-header { display: flex; justify-content: space-between; align-items: start; margin-bottom: 15px; }
            .dentist-info h2 { color: #667eea; font-size: 1.8em; margin-bottom: 5px; }
            .dentist-info h3 { color: #666; font-size: 1.2em; font-weight: normal; }
            .rating { background: #ffd700; padding: 8px 15px; border-radius: 20px; font-weight: bold; }
            .details { margin-top: 15px; line-height: 1.8; }
            .details p { margin-bottom: 8px; color: #333; }
            .insurance-badge { display: inline-block; background: #e8f4f8; color: #667eea; padding: 5px 15px; border-radius: 20px; margin-right: 10px; margin-top: 10px; font-size: 0.9em; }
            .back-btn { display: inline-block; background: white; color: #667eea; padding: 15px 30px; border-radius: 10px; text-decoration: none; font-weight: 600; margin-bottom: 20px; }
            .back-btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(255,255,255,0.3); }
            .no-results { background: white; padding: 40px; border-radius: 15px; text-align: center; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🦷 ToothSnap</h1>
            </div>
            <a href="/" class="back-btn">← New Search</a>
            <div class="results-count">Found ''' + str(len(dentists)) + ''' dentists</div>
    '''
    
    if dentists:
        for d in dentists:
            stars = '⭐' * int(d['rating'])
            html += f'''
            <div class="dentist-card">
                <div class="dentist-header">
                    <div class="dentist-info">
                        <h2>{d['practice_name']}</h2>
                        <h3>{d['name']}</h3>
                    </div>
                    <div class="rating">{stars} {d['rating']}</div>
                </div>
                <div class="details">
                    <p><strong>📍 Address:</strong> {d['address']}, {d['city']}, {d['state']} {d['zip']}</p>
                    <p><strong>📞 Phone:</strong> {d['phone']}</p>
                    <p><strong>💳 Accepts:</strong></p>
                    {''.join([f'<span class="insurance-badge">{ins}</span>' for ins in d['insurance'].split(', ')])}
                </div>
            </div>
            '''
    else:
        html += '<div class="no-results"><h2>No dentists found</h2><p>Try adjusting your search criteria</p></div>'
    
    html += '</div></body></html>'
    return html

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)

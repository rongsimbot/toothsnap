from flask import Flask, request, render_template_string, jsonify, session, redirect
import psycopg2
import os
import requests
import json
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Shopify configuration
SHOPIFY_STORE_URL = os.getenv('SHOPIFY_STORE_URL', 'simrobotics.myshopify.com')
SHOPIFY_CLIENT_ID = os.getenv('SHOPIFY_CLIENT_ID')
SHOPIFY_CLIENT_SECRET = os.getenv('SHOPIFY_CLIENT_SECRET')
SHOPIFY_API_VERSION = '2024-01'

# In-memory cache (server-side, not session)
_cache = {}

def get_shopify_token():
    """Generate Shopify OAuth token (cached in memory)"""
    cache_key = 'shopify_token'
    if cache_key in _cache and _cache.get('shopify_token_time', 0) + 82800 > time.time():
        return _cache[cache_key]
    
    response = requests.post(
        f"https://{SHOPIFY_STORE_URL}/admin/oauth/access_token",
        data={
            'grant_type': 'client_credentials',
            'client_id': SHOPIFY_CLIENT_ID,
            'client_secret': SHOPIFY_CLIENT_SECRET
        }
    )
    token = response.json()['access_token']
    _cache[cache_key] = token
    _cache['shopify_token_time'] = time.time()
    return token

def call_shopify_api(endpoint):
    """Call Shopify Admin API"""
    token = get_shopify_token()
    response = requests.get(
        f"https://{SHOPIFY_STORE_URL}/admin/api/{SHOPIFY_API_VERSION}/{endpoint}",
        headers={'X-Shopify-Access-Token': token}
    )
    return response.json()

def get_db():
    """Connect to PostgreSQL database"""
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
    """Search for dentists"""
    city = request.args.get('city', '')
    state = request.args.get('state', '')
    insurance = request.args.get('insurance', '')
    
    conn = get_db()
    cur = conn.cursor()
    
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
    
    query += " ORDER BY " + ("d.rating DESC" if any([city, state, insurance]) else "d.practice_name ASC")
    
    cur.execute(query, params)
    results = cur.fetchall()
    
    dentists = []
    for row in results:
        cur.execute('''SELECT ip.name FROM insurance_providers ip JOIN dentist_insurance di ON ip.id = di.provider_id WHERE di.dentist_id = %s''', (row[0],))
        insurance_list = [r[0] for r in cur.fetchall()]
        dentists.append({'id': row[0], 'name': row[1], 'practice_name': row[2], 'address': row[3], 'city': row[4], 'state': row[5], 'zip': row[6], 'phone': row[7], 'rating': float(row[8]) if row[8] else 0, 'insurance': ', '.join(insurance_list)})
    
    cur.close()
    conn.close()
    
    html = '''<!DOCTYPE html><html><head><title>ToothSnap - Search Results</title><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>* { margin: 0; padding: 0; box-sizing: border-box; } body { font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; } .container { max-width: 1200px; margin: 0 auto; } .header { text-align: center; color: white; margin-bottom: 40px; } .header h1 { font-size: 2.5em; margin-bottom: 10px; } .results-count { color: white; font-size: 1.2em; margin-bottom: 20px; } .dentist-card { background: white; border-radius: 15px; padding: 30px; margin-bottom: 20px; box-shadow: 0 5px 15px rgba(0,0,0,0.2); } .dentist-header { display: flex; justify-content: space-between; align-items: start; margin-bottom: 15px; } .dentist-info h2 { color: #667eea; font-size: 1.8em; margin-bottom: 5px; } .dentist-info h3 { color: #666; font-size: 1.2em; font-weight: normal; } .rating { background: #ffd700; padding: 8px 15px; border-radius: 20px; font-weight: bold; } .details { margin-top: 15px; line-height: 1.8; } .details p { margin-bottom: 8px; color: #333; } .insurance-badge { display: inline-block; background: #e8f4f8; color: #667eea; padding: 5px 15px; border-radius: 20px; margin-right: 10px; margin-top: 10px; font-size: 0.9em; } .back-btn { display: inline-block; background: white; color: #667eea; padding: 15px 30px; border-radius: 10px; text-decoration: none; font-weight: 600; margin-bottom: 20px; } .back-btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(255,255,255,0.3); } .no-results { background: white; padding: 40px; border-radius: 15px; text-align: center; }</style></head><body><div class="container"><div class="header"><h1>🦷 ToothSnap</h1></div><a href="/" class="back-btn">← New Search</a><div class="results-count">Found ''' + str(len(dentists)) + ''' dentists</div>'''
    
    if dentists:
        for d in dentists:
            stars = '⭐' * int(d['rating'])
            html += f'''<div class="dentist-card"><div class="dentist-header"><div class="dentist-info"><h2>{d['practice_name']}</h2><h3>{d['name']}</h3></div><div class="rating">{stars} {d['rating']}</div></div><div class="details"><p><strong>📍 Address:</strong> {d['address']}, {d['city']}, {d['state']} {d['zip']}</p><p><strong>📞 Phone:</strong> {d['phone']}</p><p><strong>💳 Accepts:</strong></p>{''.join([f'<span class="insurance-badge">{ins}</span>' for ins in d['insurance'].split(', ')])}</div></div>'''
    else:
        html += '<div class="no-results"><h2>No dentists found</h2><p>Try adjusting your search criteria</p></div>'
    
    html += '</div></body></html>'
    return html

# ========== E-COMMERCE ROUTES ==========

@app.route('/products')
def products():
    """Product catalog page"""
    cache_key = 'products_data'
    if cache_key in _cache and time.time() - _cache.get('products_cache_time', 0) < 300:
        products_data = _cache[cache_key]
    else:
        data = call_shopify_api('products.json?limit=250')
        products_data = data.get('products', [])
        _cache[cache_key] = products_data
        _cache['products_cache_time'] = time.time()
    
    html = f'''<!DOCTYPE html><html><head><title>ToothSnap - Products</title><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head><body><h1>Products ({len(products_data)} items)</h1><a href="/">← Back to Home</a><pre>{json.dumps(products_data[:5], indent=2)}</pre><p>... and {len(products_data) - 5} more products</p></body></html>'''
    return html

@app.route('/product/<product_id>')
def product_detail(product_id):
    """Product detail page with Add to Cart"""
    data = call_shopify_api(f'products/{product_id}.json')
    product = data.get('product', {})
    
    if not product:
        return redirect('/products')
    
    # Get first image
    image_url = product.get('images', [{}])[0].get('src', 'https://via.placeholder.com/500?text=No+Image')
    
    # Get first variant (for price and variant_id)
    variant = product.get('variants', [{}])[0]
    price = variant.get('price', '0.00')
    variant_id = variant.get('id', '')
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{product.get("title", "Product")} - ToothSnap</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            min-height: 100vh; 
            padding: 20px; 
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .back-btn {{
            display: inline-block;
            background: white;
            color: #667eea;
            padding: 12px 24px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            margin-bottom: 20px;
        }}
        .back-btn:hover {{ transform: translateY(-2px); }}
        .product-container {{
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        .product-layout {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 40px;
        }}
        .product-image {{
            width: 100%;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        .product-info h1 {{
            color: #333;
            font-size: 2.2em;
            margin-bottom: 20px;
        }}
        .product-price {{
            color: #667eea;
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 20px;
        }}
        .product-description {{
            color: #666;
            line-height: 1.8;
            margin-bottom: 30px;
        }}
        .quantity-selector {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 20px;
        }}
        .quantity-selector label {{
            font-weight: 600;
            color: #333;
        }}
        .quantity-selector input {{
            width: 80px;
            padding: 10px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 1.1em;
            text-align: center;
        }}
        .add-to-cart-btn {{
            width: 100%;
            padding: 18px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 1.3em;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
        }}
        .add-to-cart-btn:hover {{
            transform: scale(1.02);
        }}
        .success-message {{
            display: none;
            background: #4CAF50;
            color: white;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
            text-align: center;
        }}
        @media (max-width: 768px) {{
            .product-layout {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-btn">← Back to Products</a>
        <div class="product-container">
            <div class="product-layout">
                <div>
                    <img src="{image_url}" alt="{product.get('title', 'Product')}" class="product-image">
                </div>
                <div class="product-info">
                    <h1>{product.get('title', 'Product')}</h1>
                    <div class="product-price">${price}</div>
                    <div class="product-description">
                        {product.get('body_html', '<p>No description available.</p>')}
                    </div>
                    <div class="quantity-selector">
                        <label for="quantity">Quantity:</label>
                        <input type="number" id="quantity" value="1" min="1" max="10">
                    </div>
                    <button class="add-to-cart-btn" onclick="addToCart()">🛒 Add to Cart</button>
                    <div id="success-message" class="success-message">
                        ✅ Added to cart! <a href="/cart" style="color: white; text-decoration: underline;">View Cart</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        function addToCart() {{
            const quantity = document.getElementById('quantity').value;
            
            fetch('/cart/add', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json'
                }},
                body: JSON.stringify({{
                    product_id: '{product.get('id')}',
                    variant_id: '{variant_id}',
                    title: '{product.get('title', 'Product').replace("'", "\\'")}',
                    price: '{price}',
                    quantity: parseInt(quantity),
                    image: '{image_url}'
                }})
            }})
            .then(response => response.json())
            .then(data => {{
                document.getElementById('success-message').style.display = 'block';
                setTimeout(() => {{
                    window.location.href = '/checkout';
                }}, 2000);
            }})
            .catch(error => {{
                alert('Error adding to cart. Please try again.');
                console.error('Error:', error);
            }});
        }}
    </script>
</body>
</html>'''
    return html
    return html

@app.route('/cart')
def cart():
    """Shopping cart page"""
    cart_items = session.get('cart', [])
    return jsonify({'cart': cart_items, 'count': len(cart_items)})

@app.route('/cart/add', methods=['POST'])
def add_to_cart():
    """Add to cart"""
    data = request.get_json()
    cart = session.get('cart', [])
    cart.append(data)
    session['cart'] = cart
    return jsonify({'success': True, 'count': len(cart)})

@app.route('/checkout')
def checkout():
    """Redirect to Shopify"""
    cart = session.get('cart', [])
    if not cart:
        return redirect('/')
    variant_ids = [str(item.get('variant_id', '')) for item in cart]
    quantities = [str(item.get('quantity', 1)) for item in cart]
    cart_params = ','.join([f"{v}:{q}" for v, q in zip(variant_ids, quantities)])
    return redirect(f"https://{SHOPIFY_STORE_URL}/cart/{cart_params}")

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))

@app.route('/products-json')
def products_json():
    """JSON endpoint for products (used by JavaScript)"""
    cache_key = 'products_data'
    if cache_key in _cache and time.time() - _cache.get('products_cache_time', 0) < 300:
        products_data = _cache[cache_key]
    else:
        data = call_shopify_api('products.json?limit=250')
        products_data = data.get('products', [])
        _cache[cache_key] = products_data
        _cache['products_cache_time'] = time.time()
    
    return jsonify(products_data)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)

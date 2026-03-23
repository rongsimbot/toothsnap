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
    
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ToothSnap | Dentist Search Results</title>
    <script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
    <style>
        .material-symbols-outlined { font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24; }
        body { font-family: 'Inter', sans-serif; background-color: #fbf9f8; color: #1b1c1c; }
        .font-headline { font-family: 'Plus Jakarta Sans', sans-serif; }
    </style>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        "primary": "#006098", "primary-container": "#007abe", "on-primary": "#ffffff",
                        "secondary": "#006b5f", "secondary-container": "#8df5e3", "on-secondary-container": "#007165",
                        "surface": "#fbf9f8", "surface-container-low": "#f5f3f3", "surface-container-lowest": "#ffffff",
                        "on-surface": "#1b1c1c", "on-surface-variant": "#404750", "outline-variant": "#c0c7d2"
                    }
                }
            }
        }
    </script>
</head>
<body class="bg-surface text-on-surface">
    <!-- Header -->
    <header class="fixed top-0 w-full z-50 bg-[#fbf9f8]/80 backdrop-blur-xl shadow-sm">
        <div class="flex items-center w-full px-8 py-4 max-w-[1440px] mx-auto">
            <a class="text-2xl font-extrabold text-primary tracking-tighter font-headline" href="/">ToothSnap</a>
        </div>
    </header>
    
    <main class="pt-32 pb-20 px-8 max-w-4xl mx-auto">
        <div class="mb-12">
            <a href="/" class="inline-flex items-center gap-2 text-primary hover:text-primary-container font-semibold mb-6 transition-colors">
                <span class="material-symbols-outlined text-[20px]">arrow_back</span> Back to Home
            </a>
            <h1 class="text-4xl font-extrabold font-headline tracking-tight mb-2">Search Results</h1>
            <p class="text-on-surface-variant font-medium">Found ''' + str(len(dentists)) + ''' dentists matching your criteria</p>
        </div>
        
        <div class="space-y-6">
'''

    if dentists:
        for d in dentists:
            stars = ''.join(['<span class="material-symbols-outlined text-[#edc153] text-lg" style="font-variation-settings: \'FILL\' 1;">star</span>'] * int(d['rating']))
            ins_badges = ''.join([f'<span class="bg-secondary-container text-on-secondary-container px-3 py-1 rounded-full text-xs font-semibold">{ins}</span>' for ins in d['insurance'].split(', ') if ins.strip()])
            
            html += f'''
            <article class="bg-surface-container-lowest rounded-2xl p-8 border border-outline-variant/15 shadow-sm hover:shadow-md transition-shadow">
                <div class="flex justify-between items-start mb-6">
                    <div>
                        <h3 class="text-2xl font-extrabold font-headline mb-1">{d['practice_name']}</h3>
                        <p class="text-primary font-semibold text-lg">{d['name']}</p>
                    </div>
                    <div class="flex items-center gap-1 bg-[#fffdf0] px-3 py-1 rounded-full border border-[#f5e6b3]">
                        {stars}
                        <span class="font-bold ml-1 text-sm text-[#745800]">{d['rating']}</span>
                    </div>
                </div>
                
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6 pt-6 border-t border-surface-container-low">
                    <div class="flex items-start gap-3">
                        <span class="material-symbols-outlined text-outline-variant">location_on</span>
                        <div>
                            <p class="font-medium">{d['address']}</p>
                            <p class="text-on-surface-variant">{d['city']}, {d['state']} {d['zip']}</p>
                        </div>
                    </div>
                    <div class="flex items-start gap-3">
                        <span class="material-symbols-outlined text-outline-variant">call</span>
                        <p class="font-bold text-lg">{d['phone']}</p>
                    </div>
                </div>
                
                <div class="mt-8">
                    <p class="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant mb-3">Accepts Insurance</p>
                    <div class="flex flex-wrap gap-2">
                        {ins_badges}
                    </div>
                </div>
            </article>
            '''
    else:
        html += '''
        <div class="bg-surface-container-low rounded-2xl p-12 text-center border border-outline-variant/15">
            <span class="material-symbols-outlined text-5xl text-outline-variant mb-4">search_off</span>
            <h2 class="text-2xl font-bold font-headline mb-2">No dentists found</h2>
            <p class="text-on-surface-variant">Try adjusting your search criteria and try again.</p>
        </div>
        '''
        
    html += '''
        </div>
    </main>
</body>
</html>
'''
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
    
    # Calculate total
    total = sum(float(item.get('price', 0)) * int(item.get('quantity', 1)) for item in cart_items)
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Shopping Cart - ToothSnap</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            min-height: 100vh; 
            padding: 20px; 
        }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
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
        .cart-container {{
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        .cart-header {{
            font-size: 2.5em;
            color: #333;
            margin-bottom: 30px;
        }}
        .empty-cart {{
            text-align: center;
            padding: 60px 20px;
            color: #666;
        }}
        .empty-cart h2 {{
            font-size: 2em;
            margin-bottom: 20px;
        }}
        .continue-shopping {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 40px;
            border-radius: 10px;
            text-decoration: none;
            font-weight: 600;
            margin-top: 20px;
        }}
        .cart-item {{
            display: grid;
            grid-template-columns: 120px 1fr auto;
            gap: 20px;
            padding: 20px;
            border-bottom: 2px solid #f0f0f0;
            align-items: center;
        }}
        .cart-item:last-child {{
            border-bottom: none;
        }}
        .item-image {{
            width: 100%;
            border-radius: 10px;
        }}
        .item-details h3 {{
            color: #333;
            margin-bottom: 10px;
        }}
        .item-details p {{
            color: #666;
            margin-bottom: 5px;
        }}
        .item-price {{
            font-size: 1.5em;
            color: #667eea;
            font-weight: bold;
        }}
        .cart-summary {{
            margin-top: 30px;
            padding-top: 30px;
            border-top: 3px solid #667eea;
        }}
        .summary-row {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 15px;
            font-size: 1.2em;
        }}
        .summary-total {{
            font-size: 1.8em;
            font-weight: bold;
            color: #667eea;
        }}
        .checkout-btn {{
            width: 100%;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 1.4em;
            font-weight: bold;
            cursor: pointer;
            margin-top: 20px;
            transition: transform 0.2s;
        }}
        .checkout-btn:hover {{
            transform: scale(1.02);
        }}
        @media (max-width: 768px) {{
            .cart-item {{
                grid-template-columns: 80px 1fr;
            }}
            .item-price {{
                grid-column: 2;
                text-align: right;
                margin-top: 10px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-btn">← Continue Shopping</a>
        <div class="cart-container">
            <h1 class="cart-header">🛒 Shopping Cart</h1>'''
    
    if not cart_items:
        html += '''
            <div class="empty-cart">
                <h2>Your cart is empty</h2>
                <p>Add some great dental products to get started!</p>
                <a href="/" class="continue-shopping">Browse Products</a>
            </div>'''
    else:
        # Show cart items
        for item in cart_items:
            item_total = float(item.get('price', 0)) * int(item.get('quantity', 1))
            html += f'''
            <div class="cart-item">
                <img src="{item.get('image', '')}" alt="{item.get('title', 'Product')}" class="item-image">
                <div class="item-details">
                    <h3>{item.get('title', 'Product')}</h3>
                    <p>Quantity: {item.get('quantity', 1)}</p>
                    <p>Price: ${item.get('price', '0.00')} each</p>
                </div>
                <div class="item-price">${item_total:.2f}</div>
            </div>'''
        
        # Cart summary
        html += f'''
            <div class="cart-summary">
                <div class="summary-row">
                    <span>Subtotal ({len(cart_items)} items):</span>
                    <span>${total:.2f}</span>
                </div>
                <div class="summary-row summary-total">
                    <span>Total:</span>
                    <span>${total:.2f}</span>
                </div>
                <button class="checkout-btn" onclick="window.location='/checkout'">
                    Proceed to Checkout →
                </button>
            </div>'''
    
    html += '''
        </div>
    </div>
</body>
</html>'''
    return html

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


# ========== ERROR HANDLERS ==========


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

@app.errorhandler(404)
def not_found(error):
    """404 error handler"""
    return '''<!DOCTYPE html>
<html><head><title>Page Not Found - ToothSnap</title>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
    body { font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }
    .error-container { background: white; border-radius: 20px; padding: 60px 40px; text-align: center; max-width: 600px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }
    h1 { font-size: 6em; color: #667eea; margin-bottom: 20px; }
    h2 { font-size: 2em; color: #333; margin-bottom: 20px; }
    p { color: #666; font-size: 1.2em; margin-bottom: 30px; }
    a { display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 40px; border-radius: 10px; text-decoration: none; font-weight: 600; }
</style></head><body>
<div class="error-container">
    <h1>404</h1>
    <h2>Page Not Found</h2>
    <p>Sorry, the page you're looking for doesn't exist.</p>
    <a href="/">← Back to Home</a>
</div></body></html>''', 404

@app.errorhandler(500)
def internal_error(error):
    """500 error handler"""
    return '''<!DOCTYPE html>
<html><head><title>Server Error - ToothSnap</title>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
    body { font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }
    .error-container { background: white; border-radius: 20px; padding: 60px 40px; text-align: center; max-width: 600px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }
    h1 { font-size: 6em; color: #ff5252; margin-bottom: 20px; }
    h2 { font-size: 2em; color: #333; margin-bottom: 20px; }
    p { color: #666; font-size: 1.2em; margin-bottom: 30px; }
    a { display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 40px; border-radius: 10px; text-decoration: none; font-weight: 600; }
</style></head><body>
<div class="error-container">
    <h1>500</h1>
    <h2>Something Went Wrong</h2>
    <p>We're experiencing technical difficulties. Please try again later.</p>
    <a href="/">← Back to Home</a>
</div></body></html>''', 500

# ========== SECURITY & PERFORMANCE HEADERS ==========

@app.after_request
def add_security_headers(response):
    """Add security and caching headers"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Cache static assets
    if request.path.endswith(('.css', '.js', '.jpg', '.jpeg', '.png', '.gif', '.ico')):
        response.headers['Cache-Control'] = 'public, max-age=3600'
    
    return response

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)

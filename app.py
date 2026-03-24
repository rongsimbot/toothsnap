from werkzeug.security import generate_password_hash, check_password_hash
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
        cur.execute('SELECT ip.name FROM insurance_providers ip JOIN dentist_insurance di ON ip.id = di.provider_id WHERE di.dentist_id = %s', (row[0],))
        insurance_list = [r[0] for r in cur.fetchall()]
        dentists.append({
            'id': row[0], 'name': row[1], 'practice_name': row[2], 
            'address': row[3], 'city': row[4], 'state': row[5], 
            'zip': row[6], 'phone': row[7], 
            'rating': float(row[8]) if row[8] else 0, 
            'insurance': ', '.join(insurance_list)
        })
    
    cur.close()
    conn.close()
    
    # Render the new split-screen Leaflet Map layout
    dentists_json = json.dumps(dentists).replace("'", "\'")
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ToothSnap | Dentist Search Results</title>
    <script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
    
    <!-- Leaflet CSS & JS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin=""/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
    
    <style>
        .material-symbols-outlined {{ font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24; }}
        body {{ font-family: 'Inter', sans-serif; background-color: #fbf9f8; color: #1b1c1c; margin: 0; padding: 0; overflow: hidden; }}
        .font-headline {{ font-family: 'Plus Jakarta Sans', sans-serif; }}
        
        /* Map Styles */
        #map {{ height: 100vh; width: 100%; z-index: 1; }}
        
        /* Split Layout */
        .layout-wrapper {{ display: flex; height: 100vh; width: 100vw; }}
        .sidebar {{ width: 40%; min-width: 400px; max-width: 500px; height: 100vh; overflow-y: auto; background: #fbf9f8; z-index: 10; box-shadow: 4px 0 15px rgba(0,0,0,0.05); position: relative; }}
        .map-container {{ flex-grow: 1; height: 100vh; position: relative; }}
        
        .dentist-card {{ cursor: pointer; transition: all 0.2s ease; }}
        .dentist-card:hover {{ transform: translateY(-2px); box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1); border-color: #007abe; }}
        .dentist-card.active {{ border-color: #006098; background-color: #f0f7fb; }}
        
        /* Custom Marker Popup */
        .leaflet-popup-content-wrapper {{ border-radius: 12px; padding: 0; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.15); }}
        .leaflet-popup-content {{ margin: 0; }}
        .popup-header {{ background: #006098; color: white; padding: 12px 16px; }}
        .popup-body {{ padding: 12px 16px; }}
        
        @media (max-width: 768px) {{
            .layout-wrapper {{ flex-direction: column; }}
            .sidebar {{ width: 100%; min-width: 100%; height: 50vh; order: 2; }}
            .map-container {{ height: 50vh; order: 1; }}
        }}
    </style>
    <script>
        tailwind.config = {{
            theme: {{
                extend: {{
                    colors: {{
                        "primary": "#006098", "primary-container": "#007abe", "on-primary": "#ffffff",
                        "secondary": "#006b5f", "secondary-container": "#8df5e3", "on-secondary-container": "#007165",
                        "surface": "#fbf9f8", "surface-container-low": "#f5f3f3", "surface-container-lowest": "#ffffff",
                        "on-surface": "#1b1c1c", "on-surface-variant": "#404750", "outline-variant": "#c0c7d2"
                    }}
                }}
            }}
        }}
    </script>
</head>
<body>
    <div class="layout-wrapper">
        <!-- LEFT SIDEBAR: Results -->
        <aside class="sidebar flex flex-col">
            <!-- Header Sticky -->
            <div class="sticky top-0 bg-[#fbf9f8]/95 backdrop-blur-md z-20 border-b border-outline-variant/20 p-6 shadow-sm">
                <a href="/" class="inline-flex items-center gap-2 text-primary hover:text-primary-container font-semibold mb-4 transition-colors">
                    <span class="material-symbols-outlined text-[20px]">arrow_back</span> Back to Home
                </a>
                <h1 class="text-3xl font-extrabold font-headline tracking-tight mb-1">Search Results</h1>
                <p class="text-on-surface-variant font-medium text-sm">Found {len(dentists)} dentists matching your criteria</p>
            </div>
            
            <!-- List Content -->
            <div class="p-6 space-y-4" id="results-list">
"""
    if dentists:
        for i, d in enumerate(dentists):
            stars = ''.join(['<span class="material-symbols-outlined text-[#edc153] text-[16px]" style="font-variation-settings: \'FILL\' 1;">star</span>'] * int(d['rating']))
            ins_badges = ''.join([f'<span class="bg-secondary-container text-on-secondary-container px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide">{ins}</span>' for ins in d['insurance'].split(', ') if ins.strip()])
            
            html += f"""
                <article class="dentist-card bg-surface-container-lowest rounded-xl p-5 border border-outline-variant/30 shadow-sm" onclick="selectDentist({i})" id="card-{i}">
                    <div class="flex justify-between items-start mb-3">
                        <div>
                            <h3 class="text-lg font-extrabold font-headline leading-tight mb-1">{d['practice_name']}</h3>
                            <p class="text-primary font-semibold text-sm">{d['name']}</p>
                        </div>
                        <div class="flex items-center gap-0.5 bg-[#fffdf0] px-2 py-1 rounded-md border border-[#f5e6b3]">
                            {stars}
                            <span class="font-bold ml-1 text-xs text-[#745800]">{d['rating']}</span>
                        </div>
                    </div>
                    
                    <div class="grid grid-cols-1 gap-2 pt-3 border-t border-surface-container-low text-sm">
                        <div class="flex items-start gap-2">
                            <span class="material-symbols-outlined text-outline-variant text-[18px]">location_on</span>
                            <div>
                                <p class="font-medium text-on-surface">{d['address']}</p>
                                <p class="text-on-surface-variant text-xs">{d['city']}, {d['state']} {d['zip']}</p>
                            </div>
                        </div>
                        <div class="flex items-start gap-2">
                            <span class="material-symbols-outlined text-outline-variant text-[18px]">call</span>
                            <p class="font-bold text-on-surface">{d['phone']}</p>
                        </div>
                    </div>
                    
                    <div class="mt-4 pt-3 border-t border-surface-container-low">
                        <div class="flex flex-wrap gap-1.5">
                            {ins_badges}
                        </div>
                    </div>
                </article>
            """
    else:
        html += """
                <div class="bg-surface-container-low rounded-2xl p-8 text-center border border-outline-variant/15 mt-10">
                    <span class="material-symbols-outlined text-4xl text-outline-variant mb-3">search_off</span>
                    <h2 class="text-xl font-bold font-headline mb-2">No dentists found</h2>
                    <p class="text-sm text-on-surface-variant">Try adjusting your search criteria.</p>
                </div>
        """
        
    html += f"""
            </div>
        </aside>
        
        <!-- RIGHT MAP AREA -->
        <main class="map-container">
            <div id="map"></div>
        </main>
    </div>

    <script>
        const dentists = JSON.parse('{dentists_json}');
        let map = null;
        let markers = [];
        
        // Custom ToothSnap Icon
        const iconHtml = `<div style="background-color: #006098; width: 32px; height: 32px; border-radius: 50% 50% 50% 0; transform: rotate(-45deg); display: flex; align-items: center; justify-content: center; border: 3px solid white; box-shadow: 0 4px 10px rgba(0,0,0,0.3);"><div style="transform: rotate(45deg); color: white; margin-bottom: 2px;"><span class="material-symbols-outlined" style="font-size: 16px;">dentistry</span></div></div>`;
        
        const toothIcon = L.divIcon({{
            html: iconHtml,
            className: 'custom-pin',
            iconSize: [32, 32],
            iconAnchor: [16, 32],
            popupAnchor: [0, -32]
        }});

        function initMap() {{
            // Default center (US)
            let centerLat = 39.8283;
            let centerLng = -98.5795;
            let zoom = 4;
            
            map = L.map('map', {{zoomControl: false}}).setView([centerLat, centerLng], zoom);
            
            L.control.zoom({{ position: 'topright' }}).addTo(map);

            L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png', {{
                attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
                subdomains: 'abcd',
                maxZoom: 20
            }}).addTo(map);
            
            if(dentists.length > 0) {{
                geocodeAndPlot();
            }}
        }}
        
        // Simple hash function to deterministically scatter pins if they share the same ZIP code or fallback to city center
        function getFuzzyOffset(id) {{
            const seed = parseInt(id) || Math.random() * 1000;
            return ((seed * 9301 + 49297) % 233280 / 233280) * 0.04 - 0.02; // +/- 0.02 degrees
        }}

        async function geocodeAndPlot() {{
            const bounds = L.latLngBounds();
            
            // To avoid Rate Limits, we will rely heavily on cached geocoding
            for (let i = 0; i < dentists.length; i++) {{
                const d = dentists[i];
                const query = `${{d.address}}, ${{d.city}}, ${{d.state}} ${{d.zip}}`;
                const cacheKey = 'geo_' + query.replace(/\\s/g, '');
                
                let lat, lng;
                const cached = localStorage.getItem(cacheKey);
                
                if (cached) {{
                    const parsed = JSON.parse(cached);
                    lat = parsed.lat;
                    lng = parsed.lng;
                }} else {{
                    try {{
                        // Fallback generic city/state geocoding to be safe and fast if exact address fails
                        const shortQuery = `${{d.city}}, ${{d.state}}`;
                        const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${{encodeURIComponent(shortQuery)}}`);
                        const data = await res.json();
                        if (data && data.length > 0) {{
                            // add a deterministic offset so they don't overlap perfectly
                            lat = parseFloat(data[0].lat) + getFuzzyOffset(d.id + "lat");
                            lng = parseFloat(data[0].lon) + getFuzzyOffset(d.id + "lon");
                            localStorage.setItem(cacheKey, JSON.stringify({{lat, lng}}));
                        }}
                    }} catch(e) {{
                        console.error("Geocoding failed for", d.name);
                    }}
                    // Respect Nominatim rate limit (1 req/sec)
                    await new Promise(r => setTimeout(r, 1100));
                }}
                
                if (lat && lng) {{
                    const popupContent = `
                        <div class="popup-header">
                            <h4 style="font-weight: 800; font-size: 16px; margin: 0; font-family: 'Plus Jakarta Sans', sans-serif;">${{d.practice_name}}</h4>
                            <p style="margin: 0; font-size: 13px; opacity: 0.9;">${{d.name}}</p>
                        </div>
                        <div class="popup-body">
                            <p style="margin: 0 0 5px 0; font-size: 13px; display: flex; align-items: center; gap: 4px;">
                                <span class="material-symbols-outlined" style="font-size: 14px; color: #006098;">location_on</span> ${{d.address}}
                            </p>
                            <p style="margin: 0; font-size: 13px; display: flex; align-items: center; gap: 4px; font-weight: bold;">
                                <span class="material-symbols-outlined" style="font-size: 14px; color: #006098;">call</span> ${{d.phone}}
                            </p>
                        </div>
                    `;
                    
                    const marker = L.marker([lat, lng], {{icon: toothIcon}})
                        .bindPopup(popupContent, {{ closeButton: false, offset: [0, -10] }});
                        
                    marker.addTo(map);
                    markers.push(marker);
                    d._marker = marker;
                    bounds.extend([lat, lng]);
                    
                    // Center map dynamically as pins load
                    map.fitBounds(bounds, {{padding: [50, 50], maxZoom: 14}});
                }}
            }}
        }}

        function selectDentist(index) {{
            // Remove active state from all cards
            document.querySelectorAll('.dentist-card').forEach(c => c.classList.remove('active'));
            // Add active to selected
            document.getElementById('card-' + index).classList.add('active');
            
            const d = dentists[index];
            if (d._marker) {{
                map.flyTo(d._marker.getLatLng(), 15, {{
                    duration: 1.5
                }});
                d._marker.openPopup();
                
                // On mobile, scroll up to map
                if(window.innerWidth <= 768) {{
                    document.querySelector('.map-container').scrollIntoView({{behavior: 'smooth'}});
                }}
            }}
        }}

        // Initialize when DOM loads
        document.addEventListener('DOMContentLoaded', initMap);
    </script>
</body>
</html>"""
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


# ========== ADMIN ROUTES ==========


@app.route("/dentists")
def public_dentists():
    """Public page to list all dentists"""
    conn = get_db()
    cur = conn.cursor()
    
    search_query = request.args.get("q", "").strip()
    if search_query:
        # Simple case-insensitive search by name, practice_name, city, or state
        q = f"%{search_query}%"
        cur.execute("SELECT id, name, practice_name, city, state FROM dentists WHERE name ILIKE %s OR practice_name ILIKE %s OR city ILIKE %s OR state ILIKE %s ORDER BY name ASC", (q, q, q, q))
    else:
        cur.execute("SELECT id, name, practice_name, city, state FROM dentists ORDER BY name ASC")
    
    results = cur.fetchall()
    dentists = [{"id": r[0], "name": r[1], "practice_name": r[2], "city": r[3], "state": r[4]} for r in results]
    
    cur.close()
    conn.close()
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ToothSnap | Find a Dentist</title>
    <script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {{
            theme: {{
                extend: {{
                    colors: {{
                        "primary": "#006098", "primary-container": "#007abe", "on-primary": "#ffffff",
                        "surface": "#fbf9f8", "surface-container-low": "#f5f3f3", "surface-container-lowest": "#ffffff",
                        "on-surface": "#1b1c1c", "on-surface-variant": "#404750", "outline-variant": "#c0c7d2"
                    }}
                }}
            }}
        }}
    </script>
</head>
<body class="bg-surface text-on-surface">
    <!-- Navbar -->
    <nav class="bg-surface-container-lowest border-b border-outline-variant px-6 py-4 flex items-center justify-between sticky top-0 z-50 shadow-sm">
        <a href="/" class="flex items-center gap-3">
            <span class="material-symbols-outlined text-primary text-[32px] font-medium" style="font-variation-settings: 'FILL' 1">dentistry</span>
            <span class="font-bold text-2xl tracking-tight text-on-surface font-['Plus_Jakarta_Sans']">Tooth<span class="text-primary">Snap</span></span>
        </a>
        <div class="hidden md:flex gap-8 font-semibold text-[15px] text-on-surface-variant">
            <a href="/" class="hover:text-primary transition-colors">Home</a>
            <a href="/search" class="hover:text-primary transition-colors">Shop</a>
            <a href="/dentists" class="text-primary transition-colors">Find a Dentist</a>
            <a href="/dentist/register" class="hover:text-primary transition-colors">Dentist Registration</a>
        </div>
    </nav>

    <div class="max-w-6xl mx-auto py-10 px-6">
        <div class="flex justify-between items-center mb-8 flex-wrap gap-4">
            <div>
                <a href="/" class="inline-flex items-center gap-2 text-primary hover:text-primary-container font-semibold mb-4 transition-colors">
                    <span class="material-symbols-outlined text-[20px]">arrow_back</span> Back to Home
                </a>
                <h1 class="text-3xl font-extrabold font-['Plus_Jakarta_Sans'] tracking-tight">Dentist Directory</h1>
                <p class="text-on-surface-variant mt-2">Find open registry dentists near you.</p>
            </div>
            
            <form action="/dentists" method="GET" class="flex gap-2 w-full md:w-auto">
                <input type="text" name="q" placeholder="Search by name or location..." value="{search_query}" class="rounded-lg border-outline-variant focus:border-primary focus:ring-primary px-4 py-2 w-full md:w-64">
                <button type="submit" class="bg-primary text-on-primary px-4 py-2 rounded-lg font-semibold hover:bg-primary-container transition-colors">Search</button>
            </form>
        </div>

        <div class="bg-surface-container-lowest rounded-2xl shadow-sm border border-outline-variant overflow-hidden">
            <table class="w-full text-left border-collapse">
                <thead>
                    <tr class="bg-surface-container-low border-b border-outline-variant text-sm font-semibold text-on-surface-variant uppercase tracking-wider">
                        <th class="py-4 px-6">Dentist Name</th>
                        <th class="py-4 px-6 hidden sm:table-cell">Practice</th>
                        <th class="py-4 px-6">Location</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-outline-variant">
"""
    
    if not dentists:
        html += f"""
                    <tr>
                        <td colspan="3" class="py-8 px-6 text-center text-on-surface-variant">No dentists found matching "{search_query}"</td>
                    </tr>
"""
    
    for d in dentists:
        html += f"""
                    <tr class="hover:bg-surface-container-low transition-colors">
                        <td class="py-4 px-6">
                            <div class="font-bold text-on-surface">{d["name"]}</div>
                        </td>
                        <td class="py-4 px-6 hidden sm:table-cell text-on-surface-variant">{d["practice_name"] or "-"}</td>
                        <td class="py-4 px-6 text-on-surface-variant">{d["city"] or "-"}, {d["state"] or "-"}</td>
                    </tr>
"""
        
    html += """
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>"""
    return render_template_string(html)


@app.route("/dentist/register", methods=["GET", "POST"])
def dentist_register():
    """Public page for dentists to register"""
    if request.method == "POST":
        name = request.form.get("name")
        practice_name = request.form.get("practice_name", "")
        address = request.form.get("address", "")
        city = request.form.get("city", "")
        state = request.form.get("state", "")
        zip_code = request.form.get("zip", "")
        phone = request.form.get("phone", "")
        email = request.form.get("email", "")
        website = request.form.get("website", "")
        
        if not name:
            return "Name is required", 400
            
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO dentists (name, practice_name, address, city, state, zip, phone, email, website) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
                (name, practice_name, address, city, state, zip_code, phone, email, website)
            )
            dentist_id = cur.fetchone()[0]
            conn.commit()
            success = True
        except Exception as e:
            conn.rollback()
            return f"Database error: {str(e)}", 500
        finally:
            cur.close()
            conn.close()
            
        return redirect("/dentists?success=registered")
        
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ToothSnap | Dentist Registration</title>
    <script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {{
            theme: {{
                extend: {{
                    colors: {{
                        "primary": "#006098", "primary-container": "#007abe", "on-primary": "#ffffff",
                        "surface": "#fbf9f8", "surface-container-low": "#f5f3f3", "surface-container-lowest": "#ffffff",
                        "on-surface": "#1b1c1c", "on-surface-variant": "#404750", "outline-variant": "#c0c7d2"
                    }}
                }}
            }}
        }}
    </script>
</head>
<body class="bg-surface text-on-surface">
    <!-- Navbar -->
    <nav class="bg-surface-container-lowest border-b border-outline-variant px-6 py-4 flex items-center justify-between sticky top-0 z-50 shadow-sm">
        <a href="/" class="flex items-center gap-3">
            <span class="material-symbols-outlined text-primary text-[32px] font-medium" style="font-variation-settings: 'FILL' 1">dentistry</span>
            <span class="font-bold text-2xl tracking-tight text-on-surface font-['Plus_Jakarta_Sans']">Tooth<span class="text-primary">Snap</span></span>
        </a>
        <div class="hidden md:flex gap-8 font-semibold text-[15px] text-on-surface-variant">
            <a href="/" class="hover:text-primary transition-colors">Home</a>
            <a href="/search" class="hover:text-primary transition-colors">Shop</a>
            <a href="/dentists" class="hover:text-primary transition-colors">Find a Dentist</a>
            <a href="/dentist/register" class="text-primary transition-colors">Dentist Registration</a>
        </div>
    </nav>

    <div class="max-w-3xl mx-auto py-10 px-6">
        <div class="mb-8">
            <a href="/dentists" class="inline-flex items-center gap-2 text-primary hover:text-primary-container font-semibold mb-4 transition-colors">
                <span class="material-symbols-outlined text-[20px]">arrow_back</span> Back to Directory
            </a>
            <h1 class="text-3xl font-extrabold font-['Plus_Jakarta_Sans'] tracking-tight">Dentist Registration</h1>
            <p class="text-on-surface-variant mt-2">Join the ToothSnap Open Registry so patients can find you.</p>
        </div>

        <form method="POST" class="bg-surface-container-lowest rounded-2xl shadow-sm border border-outline-variant p-8 flex flex-col gap-6">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                    <label class="block text-sm font-bold text-on-surface mb-2">Full Name / Title *</label>
                    <input type="text" name="name" required placeholder="Dr. Jane Smith, DDS" class="w-full rounded-lg border-outline-variant focus:border-primary focus:ring-primary">
                </div>
                <div>
                    <label class="block text-sm font-bold text-on-surface mb-2">Practice Name</label>
                    <input type="text" name="practice_name" placeholder="Smile Care Clinic" class="w-full rounded-lg border-outline-variant focus:border-primary focus:ring-primary">
                </div>
            </div>
            
            <div class="grid grid-cols-1 gap-6">
                <div>
                    <label class="block text-sm font-bold text-on-surface mb-2">Address</label>
                    <input type="text" name="address" placeholder="123 Dental Way" class="w-full rounded-lg border-outline-variant focus:border-primary focus:ring-primary">
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                    <label class="block text-sm font-bold text-on-surface mb-2">City</label>
                    <input type="text" name="city" placeholder="Austin" class="w-full rounded-lg border-outline-variant focus:border-primary focus:ring-primary">
                </div>
                <div>
                    <label class="block text-sm font-bold text-on-surface mb-2">State</label>
                    <input type="text" name="state" placeholder="TX" class="w-full rounded-lg border-outline-variant focus:border-primary focus:ring-primary">
                </div>
                <div>
                    <label class="block text-sm font-bold text-on-surface mb-2">ZIP Code</label>
                    <input type="text" name="zip" placeholder="78701" class="w-full rounded-lg border-outline-variant focus:border-primary focus:ring-primary">
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                    <label class="block text-sm font-bold text-on-surface mb-2">Phone</label>
                    <input type="text" name="phone" placeholder="(555) 123-4567" class="w-full rounded-lg border-outline-variant focus:border-primary focus:ring-primary">
                </div>
                <div>
                    <label class="block text-sm font-bold text-on-surface mb-2">Email</label>
                    <input type="email" name="email" placeholder="doctor@smilecare.com" class="w-full rounded-lg border-outline-variant focus:border-primary focus:ring-primary">
                </div>
            </div>
            
            <div class="grid grid-cols-1 gap-6">
                <div>
                    <label class="block text-sm font-bold text-on-surface mb-2">Website</label>
                    <input type="url" name="website" placeholder="https://www.smilecare.com" class="w-full rounded-lg border-outline-variant focus:border-primary focus:ring-primary">
                </div>
            </div>

            <div class="mt-4 flex justify-end gap-4 border-t border-outline-variant pt-6">
                <a href="/dentists" class="px-6 py-3 font-bold text-on-surface-variant hover:text-on-surface transition-colors">Cancel</a>
                <button type="submit" class="bg-primary text-on-primary px-8 py-3 rounded-lg font-bold shadow-lg hover:shadow-xl transition-all">
                    Complete Registration
                </button>
            </div>
        </form>
    </div>
</body>
</html>"""
    return render_template_string(html)

@app.route('/admin/dentists')
def admin_dentists():
    """Admin page to list all dentists"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT id, name, practice_name, city, state FROM dentists ORDER BY id DESC")
    results = cur.fetchall()
    
    dentists = [{'id': r[0], 'name': r[1], 'practice_name': r[2], 'city': r[3], 'state': r[4]} for r in results]
    
    cur.close()
    conn.close()
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ToothSnap Admin | Manage Dentists</title>
    <script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {{
            theme: {{
                extend: {{
                    colors: {{
                        "primary": "#006098", "primary-container": "#007abe", "on-primary": "#ffffff",
                        "surface": "#fbf9f8", "surface-container-low": "#f5f3f3", "surface-container-lowest": "#ffffff",
                        "on-surface": "#1b1c1c", "on-surface-variant": "#404750", "outline-variant": "#c0c7d2"
                    }}
                }}
            }}
        }}
    </script>
</head>
<body class="bg-surface text-on-surface">
    <div class="max-w-6xl mx-auto py-10 px-6">
        <div class="flex justify-between items-center mb-8">
            <div>
                <a href="/" class="inline-flex items-center gap-2 text-primary hover:text-primary-container font-semibold mb-4 transition-colors">
                    <span class="material-symbols-outlined text-[20px]">arrow_back</span> Back to Home
                </a>
                <h1 class="text-3xl font-extrabold font-['Plus_Jakarta_Sans'] tracking-tight">Manage Dentists</h1>
                <p class="text-on-surface-variant mt-2">View and edit dentist profiles and insurances</p>
            </div>
            <a href="/admin/dentist/new" class="bg-primary text-on-primary px-6 py-3 rounded-lg font-bold shadow-lg hover:shadow-xl transition-all">
                + Add New Dentist
            </a>
        </div>
        
        <div class="bg-surface-container-lowest shadow-sm rounded-xl border border-outline-variant/30 overflow-hidden">
            <table class="w-full text-left border-collapse">
                <thead>
                    <tr class="bg-surface-container-low text-on-surface-variant text-sm font-bold uppercase tracking-wider border-b border-outline-variant/30">
                        <th class="p-4">ID</th>
                        <th class="p-4">Practice Name</th>
                        <th class="p-4">Dentist Name</th>
                        <th class="p-4">Location</th>
                        <th class="p-4 text-right">Actions</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-outline-variant/20">
"""
    for d in dentists:
        html += f"""
                    <tr class="hover:bg-surface/50 transition-colors">
                        <td class="p-4 text-on-surface-variant font-medium">#{d['id']}</td>
                        <td class="p-4 font-bold text-on-surface">{d['practice_name']}</td>
                        <td class="p-4 text-on-surface">{d['name']}</td>
                        <td class="p-4 text-on-surface-variant">{d['city']}, {d['state']}</td>
                        <td class="p-4 text-right">
                            <a href="/admin/dentist/{d['id']}" class="inline-flex items-center gap-1 text-primary hover:text-primary-container font-bold bg-[#f0f7fb] px-4 py-2 rounded-lg transition-colors">
                                <span class="material-symbols-outlined text-[18px]">edit</span> Edit
                            </a>
                        </td>
                    </tr>
"""
    html += """
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""
    return html

@app.route('/admin/dentist/<int:dentist_id>', methods=['GET', 'POST'])
def admin_edit_dentist(dentist_id):
    """Admin page to edit a specific dentist"""
    conn = get_db()
    cur = conn.cursor()
    
    if request.method == 'POST':
        # Process form submission
        name = request.form.get('name')
        practice_name = request.form.get('practice_name')
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        zip_code = request.form.get('zip')
        phone = request.form.get('phone')
        rating = request.form.get('rating')
        
        # Get list of checked provider IDs
        selected_insurances = request.form.getlist('insurances')
        
        try:
            # Update dentist details
            cur.execute("""
                UPDATE dentists 
                SET name=%s, practice_name=%s, address=%s, city=%s, state=%s, zip=%s, phone=%s, rating=%s
                WHERE id=%s
            """, (name, practice_name, address, city, state, zip_code, phone, rating, dentist_id))
            
            # Update insurances (delete all old mappings, insert new ones)
            cur.execute("DELETE FROM dentist_insurance WHERE dentist_id=%s", (dentist_id,))
            for provider_id in selected_insurances:
                cur.execute("INSERT INTO dentist_insurance (dentist_id, provider_id) VALUES (%s, %s)", (dentist_id, int(provider_id)))
            
            conn.commit()
            return redirect(f"/admin/dentist/{dentist_id}?success=1")
        except Exception as e:
            conn.rollback()
            return f"Database error: {str(e)}", 500
    
    # GET request - Load data
    cur.execute("SELECT id, name, practice_name, address, city, state, zip, phone, rating FROM dentists WHERE id = %s", (dentist_id,))
    d_row = cur.fetchone()
    
    if not d_row:
        return "Dentist not found", 404
        
    dentist = {
        'id': d_row[0], 'name': d_row[1], 'practice_name': d_row[2],
        'address': d_row[3], 'city': d_row[4], 'state': d_row[5],
        'zip': d_row[6], 'phone': d_row[7], 'rating': float(d_row[8]) if d_row[8] else 5.0
    }
    
    # Get all available insurances
    cur.execute("SELECT id, name FROM insurance_providers ORDER BY name ASC")
    all_insurances = [{'id': r[0], 'name': r[1]} for r in cur.fetchall()]
    
    # Get currently selected insurances for this dentist
    cur.execute("SELECT provider_id FROM dentist_insurance WHERE dentist_id = %s", (dentist_id,))
    current_insurances = [r[0] for r in cur.fetchall()]
    
    cur.close()
    conn.close()
    
    success_msg = ""
    if request.args.get('success'):
        success_msg = """
        <div class="bg-secondary-container text-on-secondary-container px-6 py-4 rounded-xl mb-6 flex items-center gap-3 font-semibold border border-[#52d1bc]">
            <span class="material-symbols-outlined">check_circle</span>
            Dentist profile updated successfully!
        </div>
        """
        
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Edit {dentist['practice_name']} | ToothSnap Admin</title>
    <script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {{
            theme: {{
                extend: {{
                    colors: {{
                        "primary": "#006098", "primary-container": "#007abe", "on-primary": "#ffffff",
                        "secondary": "#006b5f", "secondary-container": "#8df5e3", "on-secondary-container": "#007165",
                        "surface": "#fbf9f8", "surface-container-low": "#f5f3f3", "surface-container-lowest": "#ffffff",
                        "on-surface": "#1b1c1c", "on-surface-variant": "#404750", "outline-variant": "#c0c7d2"
                    }}
                }}
            }}
        }}
    </script>
</head>
<body class="bg-surface text-on-surface pb-20">
    <div class="max-w-4xl mx-auto py-10 px-6">
        <div class="mb-8">
            <a href="/admin/dentists" class="inline-flex items-center gap-2 text-primary hover:text-primary-container font-semibold mb-4 transition-colors">
                <span class="material-symbols-outlined text-[20px]">arrow_back</span> Back to Dentist List
            </a>
            <h1 class="text-3xl font-extrabold font-['Plus_Jakarta_Sans'] tracking-tight">Edit Profile</h1>
            <p class="text-on-surface-variant mt-2 text-lg">Editing <strong>{dentist['practice_name']}</strong></p>
        </div>
        
        {success_msg}
        
        <form method="POST" action="/admin/dentist/{dentist_id}" class="space-y-8">
            <!-- Basic Info Card -->
            <div class="bg-surface-container-lowest shadow-sm rounded-2xl border border-outline-variant/30 overflow-hidden">
                <div class="bg-surface-container-low px-8 py-5 border-b border-outline-variant/30">
                    <h2 class="text-xl font-bold font-['Plus_Jakarta_Sans'] flex items-center gap-2">
                        <span class="material-symbols-outlined text-primary">person</span> Basic Information
                    </h2>
                </div>
                <div class="p-8 grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <label class="block text-sm font-bold text-on-surface-variant mb-2">Practice Name</label>
                        <input type="text" name="practice_name" value="{dentist['practice_name']}" class="w-full rounded-lg border-outline-variant/50 focus:border-primary focus:ring focus:ring-primary/20 bg-surface px-4 py-3" required>
                    </div>
                    <div>
                        <label class="block text-sm font-bold text-on-surface-variant mb-2">Dentist Name</label>
                        <input type="text" name="name" value="{dentist['name']}" class="w-full rounded-lg border-outline-variant/50 focus:border-primary focus:ring focus:ring-primary/20 bg-surface px-4 py-3" required>
                    </div>
                    <div class="md:col-span-2">
                        <label class="block text-sm font-bold text-on-surface-variant mb-2">Street Address</label>
                        <input type="text" name="address" value="{dentist['address']}" class="w-full rounded-lg border-outline-variant/50 focus:border-primary focus:ring focus:ring-primary/20 bg-surface px-4 py-3" required>
                    </div>
                    <div>
                        <label class="block text-sm font-bold text-on-surface-variant mb-2">City</label>
                        <input type="text" name="city" value="{dentist['city']}" class="w-full rounded-lg border-outline-variant/50 focus:border-primary focus:ring focus:ring-primary/20 bg-surface px-4 py-3" required>
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm font-bold text-on-surface-variant mb-2">State</label>
                            <input type="text" name="state" value="{dentist['state']}" class="w-full rounded-lg border-outline-variant/50 focus:border-primary focus:ring focus:ring-primary/20 bg-surface px-4 py-3" required>
                        </div>
                        <div>
                            <label class="block text-sm font-bold text-on-surface-variant mb-2">ZIP</label>
                            <input type="text" name="zip" value="{dentist['zip']}" class="w-full rounded-lg border-outline-variant/50 focus:border-primary focus:ring focus:ring-primary/20 bg-surface px-4 py-3" required>
                        </div>
                    </div>
                    <div>
                        <label class="block text-sm font-bold text-on-surface-variant mb-2">Phone</label>
                        <input type="text" name="phone" value="{dentist['phone']}" class="w-full rounded-lg border-outline-variant/50 focus:border-primary focus:ring focus:ring-primary/20 bg-surface px-4 py-3" required>
                    </div>
                    <div>
                        <label class="block text-sm font-bold text-on-surface-variant mb-2">Rating (0-5)</label>
                        <input type="number" step="0.1" min="0" max="5" name="rating" value="{dentist['rating']}" class="w-full rounded-lg border-outline-variant/50 focus:border-primary focus:ring focus:ring-primary/20 bg-surface px-4 py-3" required>
                    </div>
                </div>
            </div>
            
            <!-- Insurances Card -->
            <div class="bg-surface-container-lowest shadow-sm rounded-2xl border border-outline-variant/30 overflow-hidden">
                <div class="bg-surface-container-low px-8 py-5 border-b border-outline-variant/30">
                    <h2 class="text-xl font-bold font-['Plus_Jakarta_Sans'] flex items-center gap-2">
                        <span class="material-symbols-outlined text-primary">verified_user</span> Accepted Insurances
                    </h2>
                </div>
                <div class="p-8">
                    <p class="text-on-surface-variant mb-6">Select all insurance providers that this practice currently accepts.</p>
                    <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
"""
    for ins in all_insurances:
        checked = "checked" if ins['id'] in current_insurances else ""
        html += f"""
                        <label class="flex items-center gap-3 p-4 rounded-xl border border-outline-variant/30 hover:bg-surface/50 cursor-pointer transition-colors has-[:checked]:border-primary has-[:checked]:bg-[#f0f7fb] has-[:checked]:shadow-sm">
                            <input type="checkbox" name="insurances" value="{ins['id']}" {checked} class="w-5 h-5 text-primary rounded border-outline-variant/50 focus:ring-primary">
                            <span class="font-semibold text-on-surface">{ins['name']}</span>
                        </label>
"""
    html += """
                    </div>
                </div>
            </div>
            
            <!-- Save Button -->
            <div class="flex justify-end gap-4 pt-4">
                <a href="/admin/dentists" class="px-8 py-4 font-bold text-on-surface-variant hover:text-on-surface transition-colors">Cancel</a>
                <button type="submit" class="bg-primary text-on-primary px-10 py-4 rounded-xl font-extrabold shadow-lg hover:shadow-xl hover:bg-primary-container transition-all flex items-center gap-2 text-lg">
                    <span class="material-symbols-outlined">save</span> Save Changes
                </button>
            </div>
        </form>
    </div>
</body>
</html>
"""
    return html

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


# --- USER AUTHENTICATION & DASHBOARD ---

def init_users_table():
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print("Error initializing users table:", e)
    finally:
        cur.close()
        conn.close()

# Try to initialize table on load
try:
    init_users_table()
except Exception as e:
    pass

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect("/dashboard")
        
    error = None
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("SELECT id, password_hash, name FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
            
            if user and check_password_hash(user[1], password):
                session["user_id"] = user[0]
                session["user_name"] = user[2]
                session["user_email"] = email
                return redirect("/dashboard")
            else:
                error = "Invalid email or password."
        except Exception as e:
            error = "Database error occurred."
        finally:
            cur.close()
            conn.close()
            
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ToothSnap | Login</title>
    <script src="https://cdn.tailwindcss.com?plugins=forms"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {{ theme: {{ extend: {{ colors: {{ "primary": "#006098", "primary-container": "#007abe", "on-primary": "#ffffff", "surface": "#fbf9f8", "on-surface": "#1b1c1c", "on-surface-variant": "#404750", "outline-variant": "#c0c7d2" }} }} }} }}
    </script>
</head>
<body class="bg-surface text-on-surface h-screen flex items-center justify-center">
    <div class="max-w-md w-full p-8 bg-white rounded-2xl shadow-lg border border-outline-variant">
        <div class="text-center mb-8">
            <h1 class="text-3xl font-extrabold font-['Plus_Jakarta_Sans'] text-primary mb-2">Welcome Back</h1>
            <p class="text-on-surface-variant">Sign in to your ToothSnap account</p>
        </div>
        
        {"<div class='bg-red-100 text-red-700 p-3 rounded-lg mb-6 text-sm text-center font-semibold'>" + str(error) + "</div>" if error else ""}
        
        <form method="POST" class="flex flex-col gap-5">
            <div>
                <label class="block text-sm font-bold mb-2">Email Address</label>
                <input type="email" name="email" required class="w-full rounded-lg border-outline-variant focus:border-primary px-4 py-2">
            </div>
            <div>
                <label class="block text-sm font-bold mb-2">Password</label>
                <input type="password" name="password" required class="w-full rounded-lg border-outline-variant focus:border-primary px-4 py-2">
            </div>
            <button type="submit" class="w-full bg-primary text-on-primary py-3 rounded-lg font-bold hover:bg-primary-container transition-colors mt-2">Sign In</button>
        </form>
        
        <p class="text-center text-sm text-on-surface-variant mt-6">
            Don't have an account? <a href="/register" class="text-primary font-bold hover:underline">Register here</a>
        </p>
        <div class="text-center mt-4">
            <a href="/" class="text-sm text-on-surface-variant hover:text-primary transition-colors flex justify-center items-center gap-1">
                <span class="material-symbols-outlined text-[16px]">arrow_back</span> Back to Home
            </a>
        </div>
    </div>
</body>
</html>"""
    return render_template_string(html)

@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect("/dashboard")
        
    error = None
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        
        if len(password) < 6:
            error = "Password must be at least 6 characters."
        else:
            hashed = generate_password_hash(password)
            conn = get_db()
            cur = conn.cursor()
            try:
                cur.execute("INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s) RETURNING id", (name, email, hashed))
                user_id = cur.fetchone()[0]
                conn.commit()
                
                session["user_id"] = user_id
                session["user_name"] = name
                session["user_email"] = email
                return redirect("/dashboard")
            except psycopg2.errors.UniqueViolation:
                conn.rollback()
                error = "Email is already registered."
            except Exception as e:
                conn.rollback()
                error = "Registration failed. Please try again."
            finally:
                cur.close()
                conn.close()
                
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ToothSnap | Register</title>
    <script src="https://cdn.tailwindcss.com?plugins=forms"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {{ theme: {{ extend: {{ colors: {{ "primary": "#006098", "primary-container": "#007abe", "on-primary": "#ffffff", "surface": "#fbf9f8", "on-surface": "#1b1c1c", "on-surface-variant": "#404750", "outline-variant": "#c0c7d2" }} }} }} }}
    </script>
</head>
<body class="bg-surface text-on-surface h-screen flex items-center justify-center">
    <div class="max-w-md w-full p-8 bg-white rounded-2xl shadow-lg border border-outline-variant">
        <div class="text-center mb-8">
            <h1 class="text-3xl font-extrabold font-['Plus_Jakarta_Sans'] text-primary mb-2">Create Account</h1>
            <p class="text-on-surface-variant">Join ToothSnap to manage your orders</p>
        </div>
        
        {"<div class='bg-red-100 text-red-700 p-3 rounded-lg mb-6 text-sm text-center font-semibold'>" + str(error) + "</div>" if error else ""}
        
        <form method="POST" class="flex flex-col gap-5">
            <div>
                <label class="block text-sm font-bold mb-2">Full Name</label>
                <input type="text" name="name" required class="w-full rounded-lg border-outline-variant focus:border-primary px-4 py-2">
            </div>
            <div>
                <label class="block text-sm font-bold mb-2">Email Address</label>
                <input type="email" name="email" required class="w-full rounded-lg border-outline-variant focus:border-primary px-4 py-2">
            </div>
            <div>
                <label class="block text-sm font-bold mb-2">Password</label>
                <input type="password" name="password" required class="w-full rounded-lg border-outline-variant focus:border-primary px-4 py-2">
            </div>
            <button type="submit" class="w-full bg-primary text-on-primary py-3 rounded-lg font-bold hover:bg-primary-container transition-colors mt-2">Register</button>
        </form>
        
        <p class="text-center text-sm text-on-surface-variant mt-6">
            Already have an account? <a href="/login" class="text-primary font-bold hover:underline">Sign in here</a>
        </p>
        <div class="text-center mt-4">
            <a href="/" class="text-sm text-on-surface-variant hover:text-primary transition-colors flex justify-center items-center gap-1">
                <span class="material-symbols-outlined text-[16px]">arrow_back</span> Back to Home
            </a>
        </div>
    </div>
</body>
</html>"""
    return render_template_string(html)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")
        
    user_name = session.get("user_name", "User")
    user_email = session.get("user_email", "")
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ToothSnap | Dashboard</title>
    <script src="https://cdn.tailwindcss.com?plugins=forms"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {{ theme: {{ extend: {{ colors: {{ "primary": "#006098", "primary-container": "#007abe", "on-primary": "#ffffff", "surface": "#fbf9f8", "on-surface": "#1b1c1c", "on-surface-variant": "#404750", "outline-variant": "#c0c7d2" }} }} }} }}
    </script>
</head>
<body class="bg-surface text-on-surface">
    <!-- Navbar -->
    <nav class="bg-white border-b border-outline-variant px-6 py-4 flex items-center justify-between sticky top-0 z-50 shadow-sm">
        <a href="/" class="flex items-center gap-3">
            <span class="material-symbols-outlined text-primary text-[32px]">dentistry</span>
            <span class="font-bold text-2xl tracking-tight font-['Plus_Jakarta_Sans']">Tooth<span class="text-primary">Snap</span></span>
        </a>
        <div class="flex items-center gap-4">
            <span class="text-sm font-semibold text-on-surface-variant">Hello, {user_name}</span>
            <a href="/logout" class="text-sm font-bold text-red-600 hover:text-red-800 transition-colors">Sign Out</a>
        </div>
    </nav>

    <div class="max-w-6xl mx-auto py-10 px-6">
        <h1 class="text-3xl font-extrabold font-['Plus_Jakarta_Sans'] mb-8">My Account</h1>
        
        <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
            <!-- Sidebar -->
            <div class="md:col-span-1 flex flex-col gap-4">
                <div class="bg-white p-6 rounded-2xl border border-outline-variant shadow-sm">
                    <h2 class="text-lg font-bold mb-2">Profile Details</h2>
                    <p class="text-sm text-on-surface-variant"><strong>Name:</strong> {user_name}</p>
                    <p class="text-sm text-on-surface-variant"><strong>Email:</strong> {user_email}</p>
                    <button class="mt-4 w-full bg-surface-container-low text-on-surface py-2 rounded-lg font-semibold border border-outline-variant hover:bg-outline-variant transition-colors text-sm">Edit Profile</button>
                </div>
            </div>
            
            <!-- Main Content -->
            <div class="md:col-span-2 flex flex-col gap-8">
                <!-- Shopping Cart Summary -->
                <div class="bg-white p-6 rounded-2xl border border-outline-variant shadow-sm">
                    <div class="flex justify-between items-center mb-6 border-b border-outline-variant pb-4">
                        <h2 class="text-xl font-bold flex items-center gap-2">
                            <span class="material-symbols-outlined text-primary">shopping_cart</span> Active Cart
                        </h2>
                        <span class="bg-primary/10 text-primary px-3 py-1 rounded-full text-xs font-bold">0 Items</span>
                    </div>
                    
                    <div class="py-8 flex flex-col items-center justify-center text-center">
                        <span class="material-symbols-outlined text-outline-variant text-[64px] mb-4">remove_shopping_cart</span>
                        <h3 class="text-lg font-bold text-on-surface">Your cart is empty</h3>
                        <p class="text-on-surface-variant text-sm mt-1 mb-6">Looks like you haven't added anything to your cart yet.</p>
                        <a href="/search" class="bg-primary text-on-primary px-6 py-3 rounded-lg font-bold shadow-sm hover:bg-primary-container transition-colors">Start Shopping</a>
                    </div>
                </div>
                
                <!-- Order History -->
                <div class="bg-white p-6 rounded-2xl border border-outline-variant shadow-sm">
                    <div class="flex justify-between items-center mb-6 border-b border-outline-variant pb-4">
                        <h2 class="text-xl font-bold flex items-center gap-2">
                            <span class="material-symbols-outlined text-primary">receipt_long</span> Past Purchases
                        </h2>
                    </div>
                    
                    <div class="py-8 flex flex-col items-center justify-center text-center">
                        <span class="material-symbols-outlined text-outline-variant text-[64px] mb-4">history</span>
                        <h3 class="text-lg font-bold text-on-surface">No recent orders</h3>
                        <p class="text-on-surface-variant text-sm mt-1">When you make a purchase, it will appear here.</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""
    return render_template_string(html)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)

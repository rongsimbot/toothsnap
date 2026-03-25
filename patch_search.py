import re

with open('app.py', 'r') as f:
    content = f.read()

# We need to replace the `def search():` function up to `return html`
pattern = re.compile(r"def search\(\):.*?return html", re.DOTALL)

new_search = r'''def search():
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
    dentists_json = json.dumps(dentists).replace("'", "\\'")
    
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
    return html'''

content = pattern.sub(new_search, content)

with open('app.py', 'w') as f:
    f.write(content)

print("Patch applied to app.py")

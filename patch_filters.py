import re

with open("app.py", "r") as f:
    code = f.read()

# 1. Update the search route to accept new parameters
old_search_backend = """    city = request.args.get('city', '')
    state = request.args.get('state', '')
    insurance = request.args.get('insurance', '')
    
    conn = get_db()
    cur = conn.cursor()
    
    query = \"\"\"
        SELECT DISTINCT d.id, d.name, d.practice_name, d.address, d.city, d.state, d.zip, d.phone, d.rating
        FROM dentists d
        LEFT JOIN dentist_insurance di ON d.id = di.dentist_id
        WHERE 1=1
    \"\"\"
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
    
    query += " ORDER BY " + ("d.rating DESC" if any([city, state, insurance]) else "d.practice_name ASC")"""

new_search_backend = """    city = request.args.get('city', '')
    state = request.args.get('state', '')
    insurance = request.args.get('insurance', '')
    min_rating = request.args.get('min_rating', '')
    specialty = request.args.get('specialty', '')
    
    conn = get_db()
    cur = conn.cursor()
    
    query = \"\"\"
        SELECT DISTINCT d.id, d.name, d.practice_name, d.address, d.city, d.state, d.zip, d.phone, d.rating, d.services
        FROM dentists d
        LEFT JOIN dentist_insurance di ON d.id = di.dentist_id
        WHERE 1=1
    \"\"\"
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
    if min_rating:
        query += " AND d.rating >= %s"
        params.append(float(min_rating))
    if specialty:
        query += " AND d.services ILIKE %s"
        params.append(f"%{specialty}%")
    
    query += " ORDER BY " + ("d.rating DESC" if any([city, state, insurance, min_rating, specialty]) else "d.practice_name ASC")"""

code = code.replace(old_search_backend, new_search_backend)

# 2. Update the dentists list generation
old_dentist_mapping = """        dentists.append({
            'id': row[0], 'name': row[1], 'practice_name': row[2], 
            'address': row[3], 'city': row[4], 'state': row[5],
            'zip': row[6], 'phone': row[7], 'rating': row[8],
            'insurance': ', '.join(insurance_list)
        })"""

new_dentist_mapping = """        dentists.append({
            'id': row[0], 'name': row[1], 'practice_name': row[2], 
            'address': row[3], 'city': row[4], 'state': row[5],
            'zip': row[6], 'phone': row[7], 'rating': row[8], 'services': row[9] if len(row)>9 else '',
            'insurance': ', '.join(insurance_list)
        })"""
code = code.replace(old_dentist_mapping, new_dentist_mapping)

# 3. Add Filter UI to search page
old_ui = """            <!-- List Header -->
            <div class="p-6 border-b border-surface-container-low flex justify-between items-center bg-surface-container-lowest">"""

new_ui = """            <!-- Filters UI -->
            <div class="p-4 border-b border-surface-container-low bg-surface-container-low">
                <form action="/search" method="GET" class="flex flex-wrap gap-4 items-end">
                    <input type="hidden" name="city" value="{city}">
                    <input type="hidden" name="state" value="{state}">
                    <input type="hidden" name="insurance" value="{insurance}">
                    
                    <div class="flex-1 min-w-[150px]">
                        <label class="block text-xs font-bold text-on-surface-variant uppercase tracking-wide mb-1">Min Rating</label>
                        <select name="min_rating" class="w-full rounded-lg border-outline-variant text-sm py-2">
                            <option value="">Any Rating</option>
                            <option value="4.5" {"selected" if request.args.get("min_rating")=="4.5" else ""}>4.5+ Stars</option>
                            <option value="4.0" {"selected" if request.args.get("min_rating")=="4.0" else ""}>4.0+ Stars</option>
                            <option value="3.0" {"selected" if request.args.get("min_rating")=="3.0" else ""}>3.0+ Stars</option>
                        </select>
                    </div>
                    
                    <div class="flex-1 min-w-[150px]">
                        <label class="block text-xs font-bold text-on-surface-variant uppercase tracking-wide mb-1">Specialty</label>
                        <select name="specialty" class="w-full rounded-lg border-outline-variant text-sm py-2">
                            <option value="">Any Specialty</option>
                            <option value="Pediatric" {"selected" if request.args.get("specialty")=="Pediatric" else ""}>Pediatric</option>
                            <option value="Orthodontics" {"selected" if request.args.get("specialty")=="Orthodontics" else ""}>Orthodontics</option>
                            <option value="Cosmetic" {"selected" if request.args.get("specialty")=="Cosmetic" else ""}>Cosmetic</option>
                            <option value="Surgery" {"selected" if request.args.get("specialty")=="Surgery" else ""}>Oral Surgery</option>
                        </select>
                    </div>
                    
                    <button type="submit" class="bg-primary text-on-primary px-4 py-2 rounded-lg text-sm font-bold hover:bg-primary-container transition-colors">Apply Filters</button>
                    <a href="/search" class="px-4 py-2 text-primary text-sm font-bold hover:bg-surface-container border border-primary rounded-lg">Clear</a>
                </form>
            </div>
            
            <!-- List Header -->
            <div class="p-6 border-b border-surface-container-low flex justify-between items-center bg-surface-container-lowest">"""
code = code.replace(old_ui, new_ui)

with open("app.py", "w") as f:
    f.write(code)

print("Patch applied for Filters")

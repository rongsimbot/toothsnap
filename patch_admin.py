import re

with open('app.py', 'r') as f:
    content = f.read()

# Let's find a good place to insert the admin routes.
# Right before `# ========== SECURITY & PERFORMANCE HEADERS ==========` is a good spot.
admin_routes = r'''
# ========== ADMIN ROUTES ==========

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
'''

if '# ========== SECURITY & PERFORMANCE HEADERS ==========' in content:
    content = content.replace('# ========== SECURITY & PERFORMANCE HEADERS ==========', admin_routes)
    with open('app.py', 'w') as f:
        f.write(content)
    print("Admin routes injected successfully.")
else:
    print("Could not find the injection point.")

import sys

with open("/home/lo/.openclaw/workspace/toothsnap/app.py", "r") as f:
    code = f.read()

# Replace the INSERT statement to include 'services'
old_insert_vars = """email = request.form.get("email", "")
        website = request.form.get("website", "")
        
        if not name:"""

new_insert_vars = """email = request.form.get("email", "")
        website = request.form.get("website", "")
        services = request.form.get("services", "")
        
        if not name:"""

old_insert_sql = """cur.execute(
                "INSERT INTO dentists (name, practice_name, address, city, state, zip, phone, email, website) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
                (name, practice_name, address, city, state, zip_code, phone, email, website)
            )"""

new_insert_sql = """cur.execute(
                "INSERT INTO dentists (name, practice_name, address, city, state, zip, phone, email, website, services) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
                (name, practice_name, address, city, state, zip_code, phone, email, website, services)
            )"""

# Update the HTML form
old_website_field = """<div>
                    <label class="block text-sm font-bold text-on-surface mb-2">Website</label>
                    <input type="url" name="website" placeholder="https://www.smilecare.com" class="w-full rounded-lg border-outline-variant focus:border-primary focus:ring-primary">
                </div>
            </div>"""

new_website_field = """<div>
                    <label class="block text-sm font-bold text-on-surface mb-2">Website</label>
                    <input type="url" name="website" placeholder="https://www.smilecare.com" class="w-full rounded-lg border-outline-variant focus:border-primary focus:ring-primary">
                </div>
            </div>
            
            <div class="grid grid-cols-1 gap-6">
                <div>
                    <label class="block text-sm font-bold text-on-surface mb-2">Dental Services Offered (Detailed)</label>
                    <textarea name="services" rows="4" placeholder="List your specialized services, treatments, equipment (e.g., Invisalign, Pediatric Dentistry, Laser Whitening)..." class="w-full rounded-lg border-outline-variant focus:border-primary focus:ring-primary"></textarea>
                </div>
            </div>"""

# Display services on the public profile page
old_phone_display = """<div class="flex items-start gap-2">
                            <span class="material-symbols-outlined text-[18px]">call</span>
                            <span>{{d['phone'] or "No phone listed"}}</span>
                        </div>"""

new_phone_display = """<div class="flex items-start gap-2">
                            <span class="material-symbols-outlined text-[18px]">call</span>
                            <span>{{d['phone'] or "No phone listed"}}</span>
                        </div>
                        <div class="flex items-start gap-2 md:col-span-2">
                            <span class="material-symbols-outlined text-[18px]">medical_services</span>
                            <span><strong>Services:</strong> {{d.get('services') or "General Dentistry"}}</span>
                        </div>"""

# Include services in SELECT
old_select_profile = """cur.execute("SELECT id, name, practice_name, address, city, state, zip, phone, website FROM dentists WHERE id = %s", (dentist_id,))"""
new_select_profile = """cur.execute("SELECT id, name, practice_name, address, city, state, zip, phone, website, services FROM dentists WHERE id = %s", (dentist_id,))"""

old_dict_profile = """"zip": dentist_row[6], "phone": dentist_row[7], "website": dentist_row[8]
    }"""
new_dict_profile = """"zip": dentist_row[6], "phone": dentist_row[7], "website": dentist_row[8], "services": dentist_row[9]
    }"""


if old_insert_vars in code:
    code = code.replace(old_insert_vars, new_insert_vars)
if old_insert_sql in code:
    code = code.replace(old_insert_sql, new_insert_sql)
if old_website_field in code:
    code = code.replace(old_website_field, new_website_field)
if old_phone_display in code:
    code = code.replace(old_phone_display, new_phone_display)
if old_select_profile in code:
    code = code.replace(old_select_profile, new_select_profile)
if old_dict_profile in code:
    code = code.replace(old_dict_profile, new_dict_profile)

with open("/home/lo/.openclaw/workspace/toothsnap/app.py", "w") as f:
    f.write(code)

print("PATCH APPLIED")

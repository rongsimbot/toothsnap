import sys

with open("/home/lo/.openclaw/workspace/toothsnap/app.py", "r") as f:
    code = f.read()

dentist_profile_routes = """
@app.route("/dentist/<int:dentist_id>", methods=["GET", "POST"])
def public_dentist(dentist_id):
    \"\"\"Public page for a specific dentist profile and reviews\"\"\"
    conn = get_db()
    cur = conn.cursor()
    
    error = None
    success = request.args.get("success")
    
    if request.method == "POST":
        if "user_id" not in session:
            return redirect("/login")
            
        rating = int(request.form.get("rating", 5))
        comment = request.form.get("comment", "")
        
        try:
            # Upsert review
            cur.execute(
                "INSERT INTO dentist_ratings (user_id, dentist_id, rating, comment) VALUES (%s, %s, %s, %s) ON CONFLICT (user_id, dentist_id) DO UPDATE SET rating = EXCLUDED.rating, comment = EXCLUDED.comment, created_at = CURRENT_TIMESTAMP",
                (session["user_id"], dentist_id, rating, comment)
            )
            conn.commit()
            
            # Update the cached rating in the dentists table using the median
            cur.execute("SELECT rating FROM dentist_ratings WHERE dentist_id = %s ORDER BY rating", (dentist_id,))
            all_ratings = [r[0] for r in cur.fetchall()]
            if all_ratings:
                n = len(all_ratings)
                median_rating = float(all_ratings[n//2]) if n % 2 == 1 else float(sum(all_ratings[n//2-1:n//2+1]) / 2.0)
                cur.execute("UPDATE dentists SET rating = %s WHERE id = %s", (median_rating, dentist_id))
                conn.commit()
            
            return redirect(f"/dentist/{dentist_id}?success=1")
        except Exception as e:
            conn.rollback()
            error = "Could not save review. " + str(e)
            
    cur.execute("SELECT id, name, practice_name, address, city, state, zip, phone, website FROM dentists WHERE id = %s", (dentist_id,))
    dentist_row = cur.fetchone()
    if not dentist_row:
        cur.close()
        conn.close()
        return "Dentist not found", 404
        
    d = {
        "id": dentist_row[0], "name": dentist_row[1], "practice_name": dentist_row[2],
        "address": dentist_row[3], "city": dentist_row[4], "state": dentist_row[5],
        "zip": dentist_row[6], "phone": dentist_row[7], "website": dentist_row[8]
    }
    
    cur.execute("SELECT ip.name FROM insurance_providers ip JOIN dentist_insurance di ON ip.id = di.provider_id WHERE di.dentist_id = %s", (dentist_id,))
    insurance_list = [r[0] for r in cur.fetchall()]
    insurance_str = ", ".join(insurance_list) if insurance_list else "None listed"
    
    cur.execute("SELECT rating FROM dentist_ratings WHERE dentist_id = %s ORDER BY rating", (dentist_id,))
    ratings = [r[0] for r in cur.fetchall()]
    
    median_rating = 0
    if ratings:
        n = len(ratings)
        median_rating = ratings[n//2] if n % 2 == 1 else sum(ratings[n//2-1:n//2+1]) / 2.0
            
    cur.execute("SELECT dr.rating, dr.comment, dr.created_at, u.name, u.id FROM dentist_ratings dr JOIN users u ON dr.user_id = u.id WHERE dr.dentist_id = %s ORDER BY dr.created_at DESC", (dentist_id,))
    reviews = [{"rating": r[0], "comment": r[1], "date": r[2].strftime("%b %d, %Y"), "user": r[3], "user_id": r[4]} for r in cur.fetchall()]
    
    cur.close()
    conn.close()
    
    is_logged_in = "user_id" in session
    current_user_id = session.get("user_id")
    
    user_existing_review = next((r for r in reviews if r["user_id"] == current_user_id), None) if is_logged_in else None
    
    def render_stars(r):
        html = '<div class="flex gap-1 text-yellow-400 text-sm">'
        for i in range(5):
            if i < r:
                html += '<span class="material-symbols-outlined" style="font-variation-settings: \\'FILL\\' 1;">star</span>'
            else:
                html += '<span class="material-symbols-outlined" style="font-variation-settings: \\'FILL\\' 0;">star</span>'
        html += '</div>'
        return html

    html_parts = []
    
    for r in reviews:
        html_parts.append(f\"\"\"
        <div class="bg-white p-6 rounded-xl border border-outline-variant shadow-sm mb-4">
            <div class="flex justify-between items-start mb-3">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center text-primary font-bold">
                        {r["user"][0].upper()}
                    </div>
                    <div>
                        <p class="font-bold">{r["user"]}</p>
                        <p class="text-xs text-on-surface-variant">{r["date"]}</p>
                    </div>
                </div>
                {render_stars(r["rating"])}
            </div>
            <p class="text-on-surface-variant text-sm mt-3 leading-relaxed">{r["comment"]}</p>
        </div>
        \"\"\")
    
    reviews_html = "".join(html_parts)
    if not reviews_html:
        reviews_html = "<p class='text-on-surface-variant italic'>No reviews yet. Be the first!</p>"
        
    form_html = f\"\"\"
        <form method="POST" class="flex flex-col gap-4">
            <div>
                <label class="block text-sm font-bold mb-2">Rating (1-5 Stars)</label>
                <select name="rating" class="w-full rounded-lg border-outline-variant focus:border-primary px-3 py-2 bg-white">
                    <option value="5" {"selected" if user_existing_review and user_existing_review["rating"] == 5 else ""}>⭐⭐⭐⭐⭐ (5 - Excellent)</option>
                    <option value="4" {"selected" if user_existing_review and user_existing_review["rating"] == 4 else ""}>⭐⭐⭐⭐ (4 - Good)</option>
                    <option value="3" {"selected" if user_existing_review and user_existing_review["rating"] == 3 else ""}>⭐⭐⭐ (3 - Average)</option>
                    <option value="2" {"selected" if user_existing_review and user_existing_review["rating"] == 2 else ""}>⭐⭐ (2 - Poor)</option>
                    <option value="1" {"selected" if user_existing_review and user_existing_review["rating"] == 1 else ""}>⭐ (1 - Terrible)</option>
                </select>
            </div>
            <div>
                <label class="block text-sm font-bold mb-2">Comments</label>
                <textarea name="comment" rows="4" required placeholder="Share your experience..." class="w-full rounded-lg border-outline-variant focus:border-primary px-3 py-2 bg-white">{user_existing_review["comment"] if user_existing_review else ""}</textarea>
            </div>
            <button type="submit" class="w-full bg-primary text-on-primary py-3 rounded-lg font-bold hover:bg-primary-container transition-colors shadow-sm">
                {"Update Review" if user_existing_review else "Submit Review"}
            </button>
        </form>
    \"\"\" if is_logged_in else f\"\"\"
        <div class="text-center py-6">
            <span class="material-symbols-outlined text-outline-variant text-[48px] mb-2">lock</span>
            <p class="text-sm text-on-surface-variant mb-4">You must be logged in to leave a review.</p>
            <a href="/login" class="inline-block w-full bg-primary text-on-primary py-2 rounded-lg font-bold hover:bg-primary-container transition-colors shadow-sm">Sign In to Review</a>
        </div>
    \"\"\"

    html = f\"\"\"<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ToothSnap | {{d['practice_name']}}</title>
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
            <span class="font-bold text-2xl tracking-tight font-['\''Plus_Jakarta_Sans'\'']">Tooth<span class="text-primary">Snap</span></span>
        </a>
        <div class="flex gap-8 font-semibold text-[15px] text-on-surface-variant">
            <a href="/dentists" class="hover:text-primary transition-colors">Directory</a>
            <a href="/search" class="hover:text-primary transition-colors">Map Search</a>
            {'<a href="/dashboard" class="text-primary">My Account</a>' if is_logged_in else '<a href="/login" class="text-primary">Sign In</a>'}
        </div>
    </nav>

    <div class="max-w-5xl mx-auto py-10 px-6">
        <div class="mb-6">
            <a href="/dentists" class="inline-flex items-center gap-2 text-primary hover:text-primary-container font-semibold mb-4 transition-colors">
                <span class="material-symbols-outlined text-[20px]">arrow_back</span> Back to Directory
            </a>
        </div>
        
        {f"<div class='bg-green-100 text-green-800 p-4 rounded-lg mb-6 font-semibold'>Review saved successfully!</div>" if success else ""}
        {f"<div class='bg-red-100 text-red-800 p-4 rounded-lg mb-6 font-semibold'>{error}</div>" if error else ""}

        <div class="bg-white p-8 rounded-2xl border border-outline-variant shadow-sm mb-8">
            <div class="flex flex-col md:flex-row justify-between md:items-start gap-6">
                <div>
                    <h1 class="text-3xl font-extrabold font-['\''Plus_Jakarta_Sans'\''] text-primary mb-1">{{d['practice_name'] or d['name']}}</h1>
                    <p class="text-lg text-on-surface-variant font-medium mb-4">{{d['name']}}</p>
                    
                    <div class="flex items-center gap-3 mb-6">
                        {render_stars(median_rating if median_rating else 0)}
                        <span class="font-bold">{f"{median_rating:.1f}" if median_rating else "No reviews yet"}</span>
                        <span class="text-on-surface-variant text-sm">({len(reviews)} reviews)</span>
                        <span class="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full font-bold ml-2">Median Score</span>
                    </div>
                    
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-on-surface-variant">
                        <div class="flex items-start gap-2">
                            <span class="material-symbols-outlined text-[18px]">location_on</span>
                            <span>{{d['address'] or ""}}<br>{{d['city'] or ""}}, {{d['state'] or ""}} {{d['zip'] or ""}}</span>
                        </div>
                        <div class="flex items-start gap-2">
                            <span class="material-symbols-outlined text-[18px]">call</span>
                            <span>{{d['phone'] or "No phone listed"}}</span>
                        </div>
                        <div class="flex items-start gap-2 md:col-span-2">
                            <span class="material-symbols-outlined text-[18px]">shield</span>
                            <span><strong>Accepted Insurances:</strong> {{insurance_str}}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
            <!-- Reviews List -->
            <div class="md:col-span-2 space-y-6">
                <h2 class="text-2xl font-bold font-['\''Plus_Jakarta_Sans'\''] border-b border-outline-variant pb-4">Patient Reviews</h2>
                
                {reviews_html}
            </div>
            
            <!-- Leave a Review Form -->
            <div class="md:col-span-1">
                <div class="bg-surface-container-low p-6 rounded-xl border border-outline-variant sticky top-24">
                    <h3 class="text-lg font-bold mb-4">{"Update Your Review" if user_existing_review else "Leave a Review"}</h3>
                    {form_html}
                </div>
            </div>
        </div>
    </div>
</body>
</html>\"\"\"
    return render_template_string(html)
"""

if "def public_dentist(dentist_id):" not in code:
    parts = code.split("if __name__ ==")
    code = parts[0] + dentist_profile_routes + "\nif __name__ ==" + parts[1]
    with open("/home/lo/.openclaw/workspace/toothsnap/app.py", "w") as f:
        f.write(code)
    print("INJECTED ROUTE")


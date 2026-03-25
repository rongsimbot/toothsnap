
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

# Script to append missing auth and admin routes to QMapp.py

routes_code = '''
# ===================== AUTH & USER MANAGEMENT =====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        # Simple auth: check against environment or hardcoded admin
        admin_user = os.environ.get('QM_ADMIN_USER', 'admin')
        admin_pass = os.environ.get('QM_ADMIN_PASS', 'admin123')
        
        if username == admin_user and password == admin_pass:
            session['username'] = username
            session['role'] = 'admin'
            session['full_name'] = 'Administrator'
            session.modified = True
            flash('Logged in successfully.', 'success')
            next_url = session.pop('_login_next', None) or url_for('index')
            return redirect(next_url)
        
        # Check credentials file for registered users
        credentials_file = Path(__file__).parent / 'auth_credentials.json'
        if credentials_file.exists():
            with open(credentials_file) as f:
                credentials = json.load(f)
            if username in credentials:
                import hashlib
                hashed = hashlib.sha256(password.encode()).hexdigest()
                if credentials[username]['password_hash'] == hashed:
                    session['username'] = username
                    session['role'] = credentials[username].get('role', 'user')
                    session['full_name'] = credentials[username].get('full_name', username)
                    session.modified = True
                    flash('Logged in successfully.', 'success')
                    next_url = session.pop('_login_next', None) or url_for('index')
                    return redirect(next_url)
        
        flash('Invalid username or password.', 'error')
        return redirect(url_for('login'))
    
    is_admin = session.get('role') == 'admin'
    return render_template('login.html', is_admin=is_admin)


@app.route('/logout', methods=['POST'])
def logout():
    """Log out and clear session."""
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new user. Admin only."""
    if request.method == 'POST':
        if session.get('role') != 'admin':
            flash('Only admins can register new users.', 'error')
            return redirect(url_for('login'))
        
        full_name = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', 'user')
        
        errors = []
        if not username:
            errors.append('Username is required.')
        if len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        confirm = request.form.get('confirm_password', '').strip()
        if password != confirm:
            errors.append('Passwords do not match.')
        
        if errors:
            for err in errors:
                flash(err, 'error')
            return render_template('register.html')
        
        # Store credentials in a JSON file
        credentials_file = Path(__file__).parent / 'auth_credentials.json'
        if credentials_file.exists():
            with open(credentials_file) as f:
                credentials = json.load(f)
        else:
            credentials = {}
        
        if username in credentials:
            flash('Username already exists.', 'error')
            return render_template('register.html')
        
        import hashlib
        hashed = hashlib.sha256(password.encode()).hexdigest()
        credentials[username] = {
            'full_name': full_name or username,
            'password_hash': hashed,
            'role': role,
            'created_at': datetime.utcnow().isoformat()
        }
        
        with open(credentials_file, 'w') as f:
            json.dump(credentials, f, indent=2)
        
        flash(f'User {username} registered successfully.', 'success')
        return redirect(url_for('list_users'))
    
    return render_template('register.html')


@app.route('/admin/list-users', methods=['GET'])
@require_role('admin')
def list_users():
    """List all registered users."""
    credentials_file = Path(__file__).parent / 'auth_credentials.json'
    if credentials_file.exists():
        with open(credentials_file) as f:
            credentials = json.load(f)
    else:
        credentials = {}
    
    users = []
    for username, data in credentials.items():
        users.append({
            'username': username,
            'full_name': data.get('full_name', username),
            'role': data.get('role', 'user'),
            'created_at': data.get('created_at', 'Unknown')
        })
    
    # Also show active sessions from flask_session directory
    session_dir = Path(__file__).parent / 'flask_session'
    active_sessions = []
    if session_dir.exists():
        for f in session_dir.iterdir():
            if f.is_file() and not f.name.startswith('.'):
                try:
                    import pickle
                    with open(f, 'rb') as sf:
                        sess_data = pickle.load(sf)
                    if sess_data.get('username'):
                        active_sessions.append({
                            'username': sess_data.get('username'),
                            'role': sess_data.get('role', 'user'),
                            'last_active': datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                        })
                except:
                    pass
    
    return render_template(
        'list_users.html',
        users=users,
        active_sessions=active_sessions
    )


@app.route('/admin/payment-schedule-config', methods=['GET'])
@require_role('admin')
def admin_payment_schedule_config():
    """Render the admin payment schedule configuration page."""
    import template_store as ts
    block = ts.get_payment_schedule_block('builder_beta')
    deposit_pct = block.get('deposit_pct', 0.10) if block else 0.10
    completion_pct = block.get('completion_pct', 0.10) if block else 0.10
    allow_user_override = block.get('allow_user_override', False) if block else False
    
    return render_template(
        'admin_payment_schedule.html',
        deposit_pct=deposit_pct,
        completion_pct=completion_pct,
        allow_user_override=allow_user_override
    )
'''

with open('app/QMapp.py', 'a') as f:
    f.write(routes_code)

print('Routes appended successfully.')
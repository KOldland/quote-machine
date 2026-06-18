import re

# Read the existing QMapp.py
with open('app/QMapp.py', 'r') as f:
    content = f.read()

# Define the old list_users function (from line 3589 to just before admin_payment_schedule_config)
old_list_users = '''def list_users():
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
def admin_payment_schedule_config():'''

new_list_users = '''def list_users():
    """List all registered users."""
    credentials_file = Path(__file__).parent / 'auth_credentials.json'
    if credentials_file.exists():
        with open(credentials_file) as f:
            credentials = json.load(f)
    else:
        credentials = {}
    
    # Return as dict matching the template's expected format
    users = {}
    for username, data in credentials.items():
        users[username] = {
            'name': data.get('full_name', username),
            'role': data.get('role', 'user')
        }
    
    return render_template(
        'list_users.html',
        users=users
    )


@app.route('/admin/promote-user/<username>', methods=['POST'])
@require_role('admin')
def promote_user(username):
    """Promote a user to admin."""
    credentials_file = Path(__file__).parent / 'auth_credentials.json'
    if credentials_file.exists():
        with open(credentials_file) as f:
            credentials = json.load(f)
        if username in credentials:
            credentials[username]['role'] = 'admin'
            with open(credentials_file, 'w') as f:
                json.dump(credentials, f, indent=2)
            flash(f'User {username} promoted to admin.', 'success')
    return redirect(url_for('list_users'))


@app.route('/admin/demote-user/<username>', methods=['POST'])
@require_role('admin')
def demote_user(username):
    """Demote a user from admin to user."""
    if username == session.get('username'):
        flash('You cannot demote yourself.', 'error')
        return redirect(url_for('list_users'))
    credentials_file = Path(__file__).parent / 'auth_credentials.json'
    if credentials_file.exists():
        with open(credentials_file) as f:
            credentials = json.load(f)
        if username in credentials:
            credentials[username]['role'] = 'user'
            with open(credentials_file, 'w') as f:
                json.dump(credentials, f, indent=2)
            flash(f'User {username} demoted to user.', 'success')
    return redirect(url_for('list_users'))


@app.route('/admin/change-password/<username>', methods=['POST'])
@require_role('admin')
def change_password(username):
    """Change a user's password."""
    credentials_file = Path(__file__).parent / 'auth_credentials.json'
    if credentials_file.exists():
        with open(credentials_file) as f:
            credentials = json.load(f)
        if username in credentials:
            new_password = request.form.get('new_password', '').strip()
            if len(new_password) >= 6:
                import hashlib
                credentials[username]['password_hash'] = hashlib.sha256(new_password.encode()).hexdigest()
                with open(credentials_file, 'w') as f:
                    json.dump(credentials, f, indent=2)
                flash(f'Password changed for {username}.', 'success')
            else:
                flash('Password must be at least 6 characters.', 'error')
    return redirect(url_for('list_users'))


@app.route('/admin/delete-user/<username>', methods=['POST'])
@require_role('admin')
def delete_user(username):
    """Delete a user."""
    if username == session.get('username'):
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('list_users'))
    if username == 'admin':
        flash('Cannot delete the default admin account.', 'error')
        return redirect(url_for('list_users'))
    credentials_file = Path(__file__).parent / 'auth_credentials.json'
    if credentials_file.exists():
        with open(credentials_file) as f:
            credentials = json.load(f)
        if username in credentials:
            del credentials[username]
            with open(credentials_file, 'w') as f:
                json.dump(credentials, f, indent=2)
            flash(f'User {username} deleted.', 'success')
    return redirect(url_for('list_users'))


@app.route('/admin/payment-schedule-config', methods=['GET'])
@require_role('admin')
def admin_payment_schedule_config():'''

# Replace in content
if old_list_users in content:
    content = content.replace(old_list_users, new_list_users, 1)
    with open('app/QMapp.py', 'w') as f:
        f.write(content)
    print('Routes updated successfully.')
else:
    print('ERROR: Could not find the old list_users function. Checking surrounding text...')
    # Debug: search for the text around the function
    idx = content.find('def list_users()')
    if idx >= 0:
        print(f'Found list_users at position {idx}')
        print('Context:', content[idx:idx+100])
    else:
        print('list_users not found at all.')
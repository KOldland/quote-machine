"with open('app/templates/index.html', 'r') as f:
    content = f.read()

old = \"<a href=\\\\"{{ url_for('list_users') }}\\" class=\\"nav-link {% if request.endpoint == 'list_users' %}active{% endif %}\\">User Management</a>\\n                        {% endif %}\\n                    </nav>\"

new = \"<a href=\\\\"{{ url_for('list_users') }}\\" class=\\"nav-link {% if request.endpoint == 'list_users' %}active{% endif %}\\">User Management</a>\\n                        <a href=\\\\"{{ url_for('admin_payment_schedule_config') }}\\" class=\\"nav-link {% if request.endpoint == 'admin_payment_schedule_config' %}active{% endif %}\\">Payment Schedule Config</a>\\n                        {% endif %}\\n                    </nav>\"

if old in content:
    content = content.replace(old, new, 1)
    with open('app/templates/index.html', 'w') as f:
        f.write(content)
    print('index.html updated successfully')
else:
    print('Could not find insertion point in index.html')
    idx = content.find('User Management')
    if idx > 0:
        print(repr(content[idx:idx+250]))
"
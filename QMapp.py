from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)

# Set a secret key for session management
app.secret_key = 'your_secret_key'

# First page route - Project Details (first page)
@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        # Store form data from the first page into session
        session['address'] = request.form.get('address')
        session['date'] = request.form.get('date')
        return redirect(url_for('page_two'))

    return render_template('form.html', first_page=True, title="Project Details")

# Second page route - Other form details (second page)
@app.route('/page-two', methods=['POST', 'GET'])
def page_two():
    if request.method == 'POST':
        # Store data from the second page into session
        session['option'] = request.form.get('option')
        return redirect(url_for('page_three'))

    return render_template('form.html', first_page=False, title="Page Two - Select Options and Details")

# Third page route - Additional details (third page)
@app.route('/page-three', methods=['POST', 'GET'])
def page_three():
    if request.method == 'POST':
        # You can add additional fields for the third page here if needed
        return redirect(url_for('submit'))

    return render_template('form.html', first_page=False, title="Page Three - Final Details")

# Final submission route
@app.route('/submit', methods=['POST', 'GET'])
def submit():
    if request.method == 'POST':
        # Collect and process all data from the session
        address = session.get('address')
        date = session.get('date')
        option = session.get('option')
        
        # Here you can process the data further (save it to a database, etc.)
        
        # Clear the session after submission if needed
        session.clear()

        return f"Form Submitted! Address: {address}, Date: {date}, Option: {option}"

    return "Something went wrong, please try again."

if __name__ == '__main__':
    app.run(debug=True)

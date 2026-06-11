import re

filepath = 'app/templates/_builder_macros.html'
with open(filepath, 'r') as f:
    content = f.read()

old_delete_q = """        var delQ = document.getElementById('btn-delete-question');
        if (delQ) {
            delQ.addEventListener('click', function() {
                if(confirm("Are you sure you want to completely delete this question?")) {
                    alert('Placeholder: Execute line_item deletion for ' + item.line_code);
                }
            });
        }"""

new_delete_q = """        var delQ = document.getElementById('btn-delete-question');
        if (delQ) {
            delQ.addEventListener('click', function() {
                if(confirm("Are you sure you want to completely delete this question?")) {
                    fetch('/builder_beta/line_item_delete', {
                        method: 'POST',
                        body: JSON.stringify({ line_code: item.line_code })
                    }).then(r => r.json()).then(d => {
                        if(d.ok || d.success) {
                            window.location.reload();
                        } else {
                            alert('Error: ' + d.error);
                        }
                    }).catch(e => alert('Network error deleting item'));
                }
            });
        }"""

if old_delete_q in content:
    content = content.replace(old_delete_q, new_delete_q)
else:
    # It might not match exactly, so we use regex
    pattern = r"var delQ = document\.getElementById\('btn-delete-question'\);.*?}\);.*?}"
    content = re.sub(pattern, new_delete_q, content, flags=re.DOTALL)

with open(filepath, 'w') as f:
    f.write(content)

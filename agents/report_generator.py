import os

def generate_report(test_name, logs, screenshots, status):

    os.makedirs("reports", exist_ok=True)

    file_path = f"reports/{test_name}.html"

    html = f"""
    <html>
    <head>
        <title>{test_name}</title>
    </head>
    <body>
        <h1>{test_name}</h1>
        <h2>Status: {status}</h2>
        <hr>
    """

    for i, log in enumerate(logs):
        html += f"<p><b>Step {i+1}:</b> {log}</p>"
        if i < len(screenshots):
            html += f"<img src='../{screenshots[i]}' width='400'><br><br>"

    html += "</body></html>"

    with open(file_path, "w") as f:
        f.write(html)

    print(f"📄 Report generated: {file_path}")
#!/usr/bin/env python3
import markdown2

# Read the markdown file
with open('anthropic_interview_prep.md', 'r') as f:
    markdown_content = f.read()

# Convert to HTML with tables and code block support
html = markdown2.markdown(markdown_content, extras=['tables', 'fenced-code-blocks', 'header-ids'])

# Create a complete HTML document with styling
html_document = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Anthropic Interview Preparation - Lee Roy Pinto</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 5px;
            margin-top: 30px;
        }}
        h3 {{
            color: #7f8c8d;
            margin-top: 20px;
        }}
        pre {{
            background-color: #f4f4f4;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
        }}
        code {{
            background-color: #f4f4f4;
            padding: 2px 5px;
            border-radius: 3px;
        }}
        blockquote {{
            border-left: 4px solid #3498db;
            padding-left: 15px;
            color: #555;
            margin: 10px 0;
        }}
        ul, ol {{
            margin-left: 20px;
        }}
        strong {{
            color: #2c3e50;
        }}
    </style>
</head>
<body>
{html}
</body>
</html>
"""

# Write the HTML file
with open('anthropic_interview_prep.html', 'w') as f:
    f.write(html_document)

print("HTML file created successfully: anthropic_interview_prep.html")
print("\nTo import to Google Docs:")
print("1. Open the HTML file in your browser")
print("2. Select all content (Cmd+A)")
print("3. Copy (Cmd+C)")
print("4. Open Google Docs")
print("5. Paste (Cmd+V)")
print("\nAlternatively, you can upload the HTML file directly to Google Drive and open with Google Docs.")
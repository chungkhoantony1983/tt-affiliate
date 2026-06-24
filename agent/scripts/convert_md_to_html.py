#!/usr/bin/env python3
"""
Markdownファイルをスタイル付きHTMLに変換するスクリプト
"""
import markdown
from pathlib import Path
import sys

def convert_md_to_html(md_file_path, output_dir):
    """MarkdownファイルをHTMLに変換"""
    md_file = Path(md_file_path)
    if not md_file.exists():
        print(f"エラー: {md_file_path} が見つかりません")
        return False

    # Markdownファイルを読み込み
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # Markdown拡張機能を有効化
    md = markdown.Markdown(extensions=[
        'tables',
        'fenced_code',
        'toc',
        'nl2br',
        'sane_lists'
    ])

    # HTMLに変換
    html_body = md.convert(md_content)

    # 完全なHTMLドキュメントを作成
    html_template = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{md_file.stem}</title>
    <style>
        @media print {{
            @page {{
                size: A4;
                margin: 20mm 15mm;
            }}
            body {{
                font-size: 10pt;
            }}
            table {{
                page-break-inside: avoid;
            }}
            h1, h2, h3 {{
                page-break-after: avoid;
            }}
        }}

        body {{
            font-family: 'Segoe UI', 'Noto Sans JP', 'Yu Gothic', 'Meiryo', sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
            background-color: #fff;
        }}

        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-top: 30px;
        }}

        h2 {{
            color: #34495e;
            border-bottom: 2px solid #95a5a6;
            padding-bottom: 8px;
            margin-top: 25px;
        }}

        h3 {{
            color: #7f8c8d;
            margin-top: 20px;
        }}

        h4 {{
            color: #95a5a6;
            margin-top: 15px;
        }}

        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
            font-size: 0.9em;
        }}

        th {{
            background-color: #3498db;
            color: white;
            font-weight: bold;
            padding: 12px 8px;
            text-align: left;
            border: 1px solid #2980b9;
        }}

        td {{
            padding: 10px 8px;
            border: 1px solid #bdc3c7;
        }}

        tr:nth-child(even) {{
            background-color: #ecf0f1;
        }}

        tr:hover {{
            background-color: #d5dbdb;
        }}

        strong, b {{
            color: #e74c3c;
            font-weight: bold;
        }}

        code {{
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 3px;
            padding: 2px 6px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 0.9em;
        }}

        pre {{
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 5px;
            padding: 15px;
            overflow-x: auto;
        }}

        pre code {{
            border: none;
            background: none;
            padding: 0;
        }}

        hr {{
            border: none;
            border-top: 2px solid #bdc3c7;
            margin: 30px 0;
        }}

        ul, ol {{
            margin: 10px 0;
            padding-left: 30px;
        }}

        li {{
            margin: 5px 0;
        }}

        blockquote {{
            border-left: 4px solid #3498db;
            padding-left: 20px;
            margin: 20px 0;
            color: #7f8c8d;
            font-style: italic;
        }}

        a {{
            color: #3498db;
            text-decoration: none;
        }}

        a:hover {{
            text-decoration: underline;
        }}

        .print-button {{
            position: fixed;
            top: 20px;
            right: 20px;
            background-color: #3498db;
            color: white;
            border: none;
            padding: 12px 24px;
            font-size: 16px;
            border-radius: 5px;
            cursor: pointer;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            z-index: 1000;
        }}

        .print-button:hover {{
            background-color: #2980b9;
        }}

        @media print {{
            .print-button {{
                display: none;
            }}
        }}
    </style>
</head>
<body>
    <button class="print-button" onclick="window.print()">📄 PDF保存</button>
    {html_body}
    <script>
        // ブラウザでPDF保存のショートカットキーをサポート
        document.addEventListener('keydown', function(e) {{
            if ((e.ctrlKey || e.metaKey) && e.key === 'p') {{
                e.preventDefault();
                window.print();
            }}
        }});
    </script>
</body>
</html>
"""

    # 出力ファイルパス
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{md_file.stem}.html"

    # HTMLファイルを保存
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_template)

    print(f"✓ HTML変換完了: {output_file}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("使用方法: python3 scripts/convert_md_to_html.py <mdファイル> <出力ディレクトリ>")
        sys.exit(1)

    md_file = sys.argv[1]
    output_dir = sys.argv[2]

    success = convert_md_to_html(md_file, output_dir)
    sys.exit(0 if success else 1)

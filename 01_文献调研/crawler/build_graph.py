# -*- coding: utf-8 -*-
"""
build_graph.py  —  生成最终可直接打开的关联图 HTML
运行后打开 data/关联图.html 即可
"""
import os, json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(SCRIPT_DIR, '..', 'data')
TPL_FILE   = os.path.join(SCRIPT_DIR, '..', 'graph_template.html')
OUT_HTML   = os.path.join(DATA_DIR, '关联图.html')
GRAPH_JSON = os.path.join(DATA_DIR, 'graph.json')

def main():
    # 先生成 graph.json
    import subprocess, sys
    gen = os.path.join(SCRIPT_DIR, 'gen_graph_data.py')
    subprocess.run([sys.executable, gen], check=True)

    with open(GRAPH_JSON, 'r', encoding='utf-8') as f:
        graph_data = f.read()

    with open(TPL_FILE, 'r', encoding='utf-8') as f:
        html = f.read()

    # 把占位符替换为真实数据
    html = html.replace('GRAPH_DATA_PLACEHOLDER', graph_data)

    with open(OUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'关联图已生成：{OUT_HTML}')
    print('直接用浏览器打开该文件即可（无需服务器）')

if __name__ == '__main__':
    main()


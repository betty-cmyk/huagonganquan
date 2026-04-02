# -*- coding: utf-8 -*-
"""
run_pipeline.py
一键执行：清洗数据 -> 生成图数据 -> 生成 docs 页面
"""

import os
import subprocess
import sys

CRAWLER_DIR = os.path.dirname(os.path.abspath(__file__))


def run(script_name):
    script_path = os.path.join(CRAWLER_DIR, script_name)
    print(f'\n[RUN] {script_name}')
    subprocess.run([sys.executable, script_path], check=True)


def main():
    run('clean_papers.py')
    run('gen_graph_v3.py')
    run('build_site.py')
    run('preprocess_writing_materials.py')
    print('\n[DONE] pipeline finished.')


if __name__ == '__main__':
    main()


#!/usr/bin/python3

import subprocess
from concurrent.futures import ThreadPoolExecutor
import os
import json
from pathlib import Path

TAG_NAME = 'dist-rocky10'
FILES_DIR = '/tmp/splits'
CHUNK_SIZE = 21

def run_sub(item):
    try:
        with open(item, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
        results = []
        for line in lines:
            result = subprocess.run(['koji', 'tag-build', TAG_NAME, str(line)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)
            results.append({
                'package': line,
                'returncode': result.returncode,
                'stdout': result.stdout.decode('utf-8').strip(),
                'stderr': result.stderr.decode('utf-8').strip()
            })
        return {
                'file': str(item),
                'results': results
        }
    except Exception as e:
        return {
                'file': str(item),
                'error': str(e)
        }

all_files = sorted(Path(FILES_DIR).glob('*'))

for i in range(0, len(all_files), CHUNK_SIZE):
    chunk = all_files[i:i + CHUNK_SIZE]
    with ThreadPoolExecutor(max_workers=CHUNK_SIZE) as executor:
        results = list(executor.map(run_sub, chunk))
        for file_result in results:
            print("Finished:", file_result['file'])
            if 'error' in file_result:
                print("Error:", file_result['error'])
            else:
                for r in file_result['results']:
                    print(f"{r['package']}: {r['returncode']}")

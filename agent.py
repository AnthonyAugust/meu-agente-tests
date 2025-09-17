#!/usr/bin/env python3
# agent.py
import os
import sys
import ast
import requests
from dotenv import load_dotenv

load_dotenv()

ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
API_KEY = os.getenv("AZURE_OPENAI_KEY")
DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")

def extract_functions(code):
    tree = ast.parse(code)
    funcs = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            args = [a.arg for a in node.args.args]
            funcs.append({"name": node.name, "args": args})
    return funcs

def build_prompt(module_name, code, funcs):
    names = ", ".join([f["name"] for f in funcs])
    prompt = f"""
You are a Python developer who writes unit tests using pytest.
Return ONLY the content of a single Python file. The FIRST line MUST be exactly:
import pytest

The file should be named test_{module_name}.py and must contain pytest test functions named def test_*.
Import the functions from the module using: from {module_name} import {names}

Do not write any explanations or markdown. Do not include code fences (```).
Write tests that include success and failure cases where appropriate (e.g., divide by zero).
Module code:
---MODULE-BEGIN---
{code}
---MODULE-END---
"""
    return prompt

def call_azure_openai(prompt):
    url = f"{ENDPOINT}/openai/deployments/{DEPLOYMENT}/chat/completions?api-version={API_VERSION}"
    headers = {"api-key": API_KEY, "Content-Type": "application/json"}
    body = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that writes pytest unit tests."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1200,
        "temperature": 0
    }
    r = requests.post(url, headers=headers, json=body)
    r.raise_for_status()
    j = r.json()
    content = j["choices"][0]["message"]["content"]
    return content

def sanitize_response(text):
    idx = text.find("import pytest")
    if idx != -1:
        return text[idx:]
    return text

def generate_basic_tests(module_name, funcs, out_path):
    lines = []
    lines.append("import pytest\n")
    lines.append(f"from {module_name} import {', '.join([f['name'] for f in funcs])}\n\n")
    for f in funcs:
        name = f["name"]
        if name.lower() in ("add", "sum", "soma"):
            lines.append(f"def test_{name}_basic():\n    assert {name}(2, 3) == 5\n\n")
        elif name.lower() in ("sub", "subtract", "subtrai", "menos"):
            lines.append(f"def test_{name}_basic():\n    assert {name}(5, 2) == 3\n\n")
        elif name.lower() in ("div", "divide", "division"):
            lines.append(f"def test_{name}_success():\n    assert {name}(6, 2) == 3\n\n")
            lines.append(f"def test_{name}_by_zero():\n    with pytest.raises(ZeroDivisionError):\n        {name}(1, 0)\n\n")
        else:
            lines.append(f"def test_{name}_exists_or_skip():\n")
            lines.append("    try:\n")
            lines.append(f"        {name}()\n")
            lines.append("    except TypeError:\n")
            lines.append("        pytest.skip('Auto-test skipped: function requires arguments')\n\n")

    with open(out_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

def main():
    if len(sys.argv) < 2:
        print("Uso: python agent.py caminho/para/modulo.py")
        sys.exit(1)

    input_path = sys.argv[1]
    with open(input_path, "r", encoding="utf-8") as f:
        code = f.read()

    module_name = os.path.splitext(os.path.basename(input_path))[0]
    funcs = extract_functions(code)
    if not funcs:
        print("Nenhuma função encontrada no arquivo. Adicione funções e tente novamente.")
        sys.exit(1)

    os.makedirs("tests", exist_ok=True)
    out_path = os.path.join("tests", f"test_{module_name}.py")

    if not (ENDPOINT and API_KEY and DEPLOYMENT):
        print("Variáveis AZURE não configuradas. Gerando testes básicos (modo fallback).")
        generate_basic_tests(module_name, funcs, out_path)
        print(f"Arquivo de testes gerado: {out_path}")
        return

    prompt = build_prompt(module_name, code, funcs)
    print("Chamando Azure OpenAI para gerar os testes...")
    try:
        response = call_azure_openai(prompt)
        response = sanitize_response(response)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(response)
        print(f"Arquivo de testes gerado: {out_path}")
    except Exception as e:
        print("Erro ao chamar Azure OpenAI:", e)
        print("Gerando testes básicos como fallback.")
        generate_basic_tests(module_name, funcs, out_path)
        print(f"Arquivo de testes gerado: {out_path}")

if __name__ == "__main__":
    main()
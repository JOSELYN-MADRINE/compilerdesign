"""
Web frontend for the Python Compiler.
Run:  python3 app.py
Then open:  http://localhost:5000
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, render_template, request, jsonify
from compiler import Compiler

app      = Flask(__name__)
compiler = Compiler()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/compile', methods=['POST'])
def compile_route():
    data        = request.get_json(force=True)
    source      = data.get('source', '')
    parser_type = 'topdown'
    execute     = data.get('execute', False)

    if not source.strip():
        return jsonify({'error': 'No source code provided'}), 400

    res = compiler.compile(source, parser_type, execute=execute)

    tokens_data = [
        {'type': t.type.name, 'value': t.value, 'line': t.line, 'col': t.col}
        for t in res.get('tokens', [])
    ]

    total_errors = (
        len(res.get('lex_errors',   [])) +
        len(res.get('parse_errors', [])) +
        len(res.get('sem_errors',   []))
    )

    return jsonify({
        'tokens':       tokens_data,
        'lex_errors':   res.get('lex_errors',   []),
        'ast_text':     res.get('ast_text',     ''),
        'parse_errors': res.get('parse_errors', []),
        'parse_steps':  res.get('parse_steps',  []),
        'sem_errors':   res.get('sem_errors',   []),
        'sem_warnings': res.get('sem_warnings', []),
        'sem_log':      res.get('sem_log',      []),
        'issues':       res.get('issues',       {}),
        'symbol_table': res.get('symbol_table', {}),
        'exe_output':   res.get('exe_output',   []),
        'exe_errors':   res.get('exe_errors',   []),
        'exe_log':      res.get('exe_log',      []),
        'success':      res.get('success',      False),
        'executed':     res.get('executed',     False),
        'parser_type':  res.get('parser_type', parser_type),
        'stats': {
            'tokens':  len(tokens_data),
            'lines':   len(source.splitlines()),
            'errors':  total_errors,
            'symbols': len(res.get('symbol_table', {})),
        },
    })


if __name__ == '__main__':
    print('\n  Compiler Web UI →  http://localhost:5000\n')
    app.run(debug=False, port=5000)

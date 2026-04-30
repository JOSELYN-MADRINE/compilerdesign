"""Compiler orchestrator – runs all three phases + optional execution."""

from lexer        import Lexer
from parser_td    import TopDownParser
from parser_bu    import BottomUpParser
from semantic     import SemanticAnalyzer
from interpreter  import Interpreter
from ast_nodes    import *
from typing       import Dict, Any


# ═══════════════════════════════════════════════════════════════ AST printer ═

def format_ast(node: ASTNode, indent: int = 0) -> str:
    pad = "  " * indent
    if node is None:
        return f"{pad}None"

    if isinstance(node, Program):
        lines = [f"{pad}Program"]
        for s in node.statements:
            lines.append(format_ast(s, indent + 1))
        return '\n'.join(lines)

    if isinstance(node, Block):
        lines = [f"{pad}Block"]
        for s in node.statements:
            lines.append(format_ast(s, indent + 1))
        return '\n'.join(lines)

    if isinstance(node, DeclStmt):
        head = f"{pad}DeclStmt [{node.var_type}] {node.name}"
        if node.initializer:
            return head + "\n" + format_ast(node.initializer, indent + 1)
        return head

    if isinstance(node, AssignStmt):
        return (f"{pad}AssignStmt {node.name} =\n"
                + format_ast(node.value, indent + 1))

    if isinstance(node, IfStmt):
        parts = [f"{pad}IfStmt",
                 f"{pad}  condition:",
                 format_ast(node.condition, indent + 2),
                 f"{pad}  then:",
                 format_ast(node.then_block, indent + 2)]
        if node.else_block:
            parts += [f"{pad}  else:",
                      format_ast(node.else_block, indent + 2)]
        return '\n'.join(parts)

    if isinstance(node, WhileStmt):
        return '\n'.join([
            f"{pad}WhileStmt",
            f"{pad}  condition:",
            format_ast(node.condition, indent + 2),
            f"{pad}  body:",
            format_ast(node.body, indent + 2),
        ])

    if isinstance(node, PrintStmt):
        return f"{pad}PrintStmt\n" + format_ast(node.value, indent + 1)

    if isinstance(node, BinaryExpr):
        return '\n'.join([
            f"{pad}BinaryExpr ( {node.op} )",
            format_ast(node.left,  indent + 1),
            format_ast(node.right, indent + 1),
        ])

    if isinstance(node, UnaryExpr):
        return f"{pad}UnaryExpr ( {node.op} )\n" + format_ast(node.operand, indent + 1)

    if isinstance(node, NumberLiteral):
        t = 'int' if node.is_int else 'float'
        return f"{pad}Literal [{t}] {node.value}"

    if isinstance(node, StringLiteral):
        return f'{pad}Literal [string] "{node.value}"'

    if isinstance(node, BoolLiteral):
        return f"{pad}Literal [bool] {node.value}"

    if isinstance(node, Identifier):
        return f"{pad}Identifier  {node.name}"

    return f"{pad}{type(node).__name__}"


# ═══════════════════════════════════════════════════════════════ Compiler ════

class Compiler:
    def compile(self, source: str, parser_type: str = 'topdown',
                execute: bool = False) -> Dict[str, Any]:
        results: Dict[str, Any] = {
            'parser_type':    parser_type,
            'tokens':         [],
            'lex_errors':     [],
            'ast':            None,
            'ast_text':       '',
            'parse_errors':   [],
            'parse_steps':    [],
            'sem_errors':     [],
            'sem_warnings':   [],
            'symbol_table':   {},
            'sem_log':        [],
            'success':        False,
            # execution fields
            'exe_output':     [],
            'exe_errors':     [],
            'exe_log':        [],
            'executed':       False,
        }

        # ── Phase 1: Lexical Analysis ─────────────────────────────────────────
        lexer = Lexer(source)
        tokens, lex_errors = lexer.tokenize()
        results['tokens']     = tokens
        results['lex_errors'] = lex_errors
        if lex_errors:
            return results

        # ── Phase 2: Syntax Analysis ──────────────────────────────────────────
        parser = (TopDownParser(tokens)
                  if parser_type == 'topdown'
                  else BottomUpParser(tokens))
        ast, parse_errors, parse_steps = parser.parse()
        results['ast']          = ast
        results['parse_errors'] = parse_errors
        results['parse_steps']  = parse_steps
        if ast:
            results['ast_text'] = format_ast(ast)
        if parse_errors:
            return results

        # ── Phase 3: Semantic Analysis ────────────────────────────────────────
        if ast:
            analyser = SemanticAnalyzer()
            sem_errors, sem_warnings, sym_table, sem_log = analyser.analyze(ast)
            results['sem_errors']   = sem_errors
            results['sem_warnings'] = sem_warnings
            results['sem_log']      = sem_log
            results['symbol_table'] = {
                name: f"{sym.var_type}   (line {sym.line})"
                for name, sym in sym_table.all_symbols().items()
            }
            if not sem_errors:
                results['success'] = True

        # ── Phase 4: Execution (optional) ─────────────────────────────────────
        if execute and results['success'] and ast:
            interp = Interpreter()
            output, exe_errors, exe_log = interp.run(ast)
            results['exe_output']  = output
            results['exe_errors']  = exe_errors
            results['exe_log']     = exe_log
            results['executed']    = True

        return results

"""Compiler orchestrator – runs all three phases + optional execution."""

from lexer        import Lexer
from parser_td    import TopDownParser
from parser_bu    import BottomUpParser
from semantic     import SemanticAnalyzer
from interpreter  import Interpreter
from ast_nodes    import *
from typing       import Dict, Any


# ═══════════════════════════════════════════════════════════════ AST printer ═

def format_ast(node: ASTNode, prefix: str = "", is_last: bool = True, is_root: bool = True) -> str:
    """Format an AST node as a hierarchical tree string."""
    if node is None:
        return f"{prefix}{'└── ' if is_last else '├── '}None"

    # Don't draw branch for the root node
    if is_root:
        branch = ""
        child_prefix = prefix
    else:
        branch = "└── " if is_last else "├── "
        child_prefix = prefix + ("    " if is_last else "│   ")

    def format_children(children_items):
        """Helper to format a list of (label, child_node) or just child_nodes."""
        lines = []
        for i, item in enumerate(children_items):
            is_last_child = (i == len(children_items) - 1)
            
            if isinstance(item, tuple):
                label, child = item
                if child is not None:
                    # For labeled children (like 'condition:', 'then:')
                    lines.append(f"{child_prefix}{'└── ' if is_last_child else '├── '}{label}")
                    sub_prefix = child_prefix + ("    " if is_last_child else "│   ")
                    # Pass is_root=False for all nested calls
                    lines.append(format_ast(child, sub_prefix, True, False))
            else:
                # Pass is_root=False for all nested children
                lines.append(format_ast(item, child_prefix, is_last_child, False))
        return lines

    if isinstance(node, Program):
        result = [f"{prefix}{branch}Program"]
        result.extend(format_children(node.statements))
        return '\n'.join(result)

    if isinstance(node, Block):
        result = [f"{prefix}{branch}Block"]
        result.extend(format_children(node.statements))
        return '\n'.join(result)

    if isinstance(node, DeclStmt):
        result = [f"{prefix}{branch}DeclStmt [{node.var_type}] {node.name}"]
        if node.initializer:
            result.extend(format_children([node.initializer]))
        return '\n'.join(result)

    if isinstance(node, AssignStmt):
        result = [f"{prefix}{branch}AssignStmt {node.name} ="]
        result.extend(format_children([node.value]))
        return '\n'.join(result)

    if isinstance(node, IfStmt):
        result = [f"{prefix}{branch}IfStmt"]
        children = [("condition:", node.condition), ("then:", node.then_block)]
        if node.else_block:
            children.append(("else:", node.else_block))
        result.extend(format_children(children))
        return '\n'.join(result)

    if isinstance(node, WhileStmt):
        result = [f"{prefix}{branch}WhileStmt"]
        children = [("condition:", node.condition), ("body:", node.body)]
        result.extend(format_children(children))
        return '\n'.join(result)

    if isinstance(node, PrintStmt):
        result = [f"{prefix}{branch}PrintStmt"]
        result.extend(format_children([node.value]))
        return '\n'.join(result)

    if isinstance(node, BinaryExpr):
        result = [f"{prefix}{branch}BinaryExpr ( {node.op} )"]
        result.extend(format_children([node.left, node.right]))
        return '\n'.join(result)

    if isinstance(node, UnaryExpr):
        result = [f"{prefix}{branch}UnaryExpr ( {node.op} )"]
        result.extend(format_children([node.operand]))
        return '\n'.join(result)

    if isinstance(node, NumberLiteral):
        t = 'int' if node.is_int else 'float'
        return f"{prefix}{branch}Literal [{t}] {node.value}"

    if isinstance(node, StringLiteral):
        return f'{prefix}{branch}Literal [string] "{node.value}"'

    if isinstance(node, BoolLiteral):
        return f"{prefix}{branch}Literal [bool] {node.value}"

    if isinstance(node, Identifier):
        return f"{prefix}{branch}Identifier {node.name}"

    return f"{prefix}{branch}{type(node).__name__}"


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

        # ── Phase 2: Syntax Analysis ────────────
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

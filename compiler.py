"""Compiler orchestrator – runs all three phases + optional execution."""

from lexer        import Lexer
from parser_td    import TopDownParser
from parser_bu    import BottomUpParser
from semantic     import SemanticAnalyzer
from interpreter  import Interpreter
from ast_nodes    import *
from tokens       import TokenType
from typing       import Dict, Any, List, Optional
import re


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

def _issue(phase: str, kind: str, message: str, *, line: Optional[int] = None,
           col: Optional[int] = None, token: Optional[str] = None,
           severity: str = 'error') -> Dict[str, Any]:
    return {
        'phase': phase,
        'kind': kind,
        'message': message,
        'line': line,
        'col': col,
        'token': token,
        'severity': severity,
    }


def _classify_lexer_errors(errors: List[str]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    for err in errors:
        m = re.match(r"Line (\d+), Col (\d+): Unknown character '(.+)'", err)
        if m:
            line, col, ch = int(m.group(1)), int(m.group(2)), m.group(3)
            issues.append(_issue(
                'lexer', 'unknown_character',
                f"Unknown character {ch!r}. Remove it or replace it with a valid token.",
                line=line, col=col, token=ch,
            ))
            continue

        m = re.match(r"Line (\d+): Unterminated string literal", err)
        if m:
            line = int(m.group(1))
            issues.append(_issue(
                'lexer', 'unterminated_string',
                'String literal is missing a closing quote.',
                line=line,
            ))
            continue

        issues.append(_issue('lexer', 'lexical_error', err))
    return issues


def _classify_parser_errors(errors: List[str]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    for err in errors:
        m = re.match(r"Line (\d+): Expected (\w+), got (\w+) \('([^']*)'\)", err)
        if m:
            line, expected, got, token = int(m.group(1)), m.group(2), m.group(3), m.group(4)
            issues.append(_issue(
                'parser', 'syntax_error',
                f"Expected {expected}, but got {got} ({token!r}).",
                line=line, token=token,
            ))
            continue

        m = re.match(r"Line (\d+): Unexpected token '([^']+)' in expression", err)
        if m:
            line, token = int(m.group(1)), m.group(2)
            issues.append(_issue(
                'parser', 'unexpected_token',
                f"Unexpected token {token!r} in an expression.",
                line=line, token=token,
            ))
            continue

        m = re.match(r"Line (\d+): Unexpected token '([^']+)'", err)
        if m:
            line, token = int(m.group(1)), m.group(2)
            issues.append(_issue(
                'parser', 'unexpected_token',
                f"Unexpected token {token!r}.",
                line=line, token=token,
            ))
            continue

        issues.append(_issue('parser', 'syntax_error', err))
    return issues


def _classify_semantic_errors(errors: List[str], warnings: List[str]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []

    def add_from_message(msg: str, severity: str = 'error') -> None:
        patterns = [
            (r"Line (\d+): Variable '([^']+)' already declared in this scope",
             'redeclaration', 'Variable {name!r} is already declared in this scope.'),
            (r"Line (\d+): Undefined variable '([^']+)'",
             'undeclared_variable', 'Variable {name!r} is not declared before use.'),
            (r"Line (\d+): Cannot assign ([^ ]+) to ([^ ]+) variable '([^']+)'",
             'type_mismatch', "Cannot assign {src} to {target} variable {name!r}."),
            (r"Line (\d+): if-condition is '([^']+)', expected 'bool'",
             'condition_type_mismatch', "If condition has type {src!r}; expected bool."),
            (r"Line (\d+): while-condition is '([^']+)', expected 'bool'",
             'condition_type_mismatch', "While condition has type {src!r}; expected bool."),
            (r"Operator '!' requires bool, got '([^']+)'",
             'invalid_operand', "Operator '!' requires a bool operand, got {src!r}."),
            (r"Unary '-' requires numeric, got '([^']+)'",
             'invalid_operand', "Unary '-' requires a numeric operand, got {src!r}."),
            (r"Operator '([+\-*/%])' requires numeric operands, got '([^']+)' and '([^']+)'",
             'type_mismatch', "Operator {op!r} requires numeric operands, got {left!r} and {right!r}."),
            (r"Cannot compare '([^']+)' with '([^']+)'",
             'invalid_comparison', "Cannot compare {left!r} with {right!r}."),
            (r"Operator '(&&|\|\|)' expects bool operands, got '([^']+)' and '([^']+)'",
             'invalid_operand', "Operator {op!r} expects bool operands, got {left!r} and {right!r}."),
        ]

        for pattern, kind, template in patterns:
            m = re.match(pattern, msg)
            if not m:
                continue
            line = int(m.group(1)) if m.group(1).isdigit() else None
            payload = {'phase': 'semantic', 'kind': kind, 'message': msg, 'severity': severity, 'line': line}
            if kind == 'redeclaration' or kind == 'undeclared_variable':
                payload['token'] = m.group(2)
                payload['message'] = template.format(name=m.group(2))
            elif kind == 'type_mismatch' and 'variable' in template:
                payload['token'] = m.group(4)
                payload['message'] = template.format(src=m.group(2), target=m.group(3), name=m.group(4))
            elif kind == 'condition_type_mismatch':
                payload['message'] = template.format(src=m.group(2))
            elif kind == 'invalid_operand' and msg.startswith("Operator '!'"):
                payload['message'] = template.format(src=m.group(1))
            elif kind == 'invalid_operand' and msg.startswith("Unary '-"):
                payload['message'] = template.format(src=m.group(1))
            elif kind == 'type_mismatch':
                payload['message'] = template.format(op=m.group(1), left=m.group(2), right=m.group(3))
            elif kind == 'invalid_comparison':
                payload['message'] = template.format(left=m.group(1), right=m.group(2))
            elif kind == 'invalid_operand' and msg.startswith("Operator '"):
                payload['message'] = template.format(op=m.group(1), left=m.group(2), right=m.group(3))
            issues.append(payload)
            return

        issues.append(_issue('semantic', 'semantic_error', msg, severity=severity))

    for err in errors:
        add_from_message(err, 'error')
    for warn in warnings:
        add_from_message(warn, 'warning')
    return issues

class Compiler:
    def compile(self, source: str, parser_type: str = 'auto',
                execute: bool = False) -> Dict[str, Any]:
        results: Dict[str, Any] = {
            'parser_type':    parser_type,
            'tokens':         [],
            'lex_errors':     [],
            'issues':         {'lexer': [], 'parser': [], 'semantic': [], 'warnings': [], 'runtime': []},
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
            results['issues']['lexer'] = _classify_lexer_errors(lex_errors)
            return results

        # ── Phase 2: Syntax Analysis with automatic parser selection ────────
        chosen_parser = parser_type

        def parse_with(parser_cls):
            parser = parser_cls(tokens)
            ast, errors, steps = parser.parse()
            return ast, errors, steps

        def prefer_bottomup_first() -> bool:
            """Use Bottom-Up first for code that looks more nested or operator-heavy."""
            token_types = [t.type for t in tokens]

            control_flow = sum(1 for t in token_types if t in (
                TokenType.KW_IF, TokenType.KW_ELSE, TokenType.KW_WHILE
            ))
            logical_ops = sum(1 for t in token_types if t in (
                TokenType.AND, TokenType.OR
            ))
            comparison_ops = sum(1 for t in token_types if t in (
                TokenType.EQ, TokenType.NEQ, TokenType.LT, TokenType.GT,
                TokenType.LTE, TokenType.GTE
            ))
            arithmetic_ops = sum(1 for t in token_types if t in (
                TokenType.PLUS, TokenType.MINUS, TokenType.MULTIPLY,
                TokenType.DIVIDE, TokenType.MODULO
            ))

            brace_depth = 0
            max_brace_depth = 0
            paren_depth = 0
            max_paren_depth = 0
            for tok in tokens:
                if tok.type == TokenType.LBRACE:
                    brace_depth += 1
                    max_brace_depth = max(max_brace_depth, brace_depth)
                elif tok.type == TokenType.RBRACE:
                    brace_depth = max(brace_depth - 1, 0)
                elif tok.type == TokenType.LPAREN:
                    paren_depth += 1
                    max_paren_depth = max(max_paren_depth, paren_depth)
                elif tok.type == TokenType.RPAREN:
                    paren_depth = max(paren_depth - 1, 0)

            complexity_score = 0
            if control_flow:
                complexity_score += 2
            if logical_ops:
                complexity_score += 2
            if comparison_ops >= 2:
                complexity_score += 1
            if arithmetic_ops >= 4:
                complexity_score += 1
            if max_brace_depth >= 2:
                complexity_score += 3
            if max_paren_depth >= 3:
                complexity_score += 2
            if len(tokens) >= 40:
                complexity_score += 2

            return complexity_score >= 4

        if parser_type == 'topdown':
            ast, parse_errors, parse_steps = parse_with(TopDownParser)
        elif parser_type == 'bottomup':
            ast, parse_errors, parse_steps = parse_with(BottomUpParser)
        else:
            if prefer_bottomup_first():
                ast, parse_errors, parse_steps = parse_with(BottomUpParser)
                chosen_parser = 'bottomup'
                if not ast or parse_errors:
                    ast, parse_errors, parse_steps = parse_with(TopDownParser)
                    if ast and not parse_errors:
                        chosen_parser = 'topdown'
            else:
                ast, parse_errors, parse_steps = parse_with(TopDownParser)
                if not ast or parse_errors:
                    ast, parse_errors, parse_steps = parse_with(BottomUpParser)
                    chosen_parser = 'bottomup'
                else:
                    chosen_parser = 'topdown'

        results['parser_type'] = chosen_parser
        results['ast']          = ast
        results['parse_errors'] = parse_errors
        results['parse_steps']  = parse_steps
        results['issues']['parser'] = _classify_parser_errors(parse_errors)
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
            results['issues']['semantic'] = _classify_semantic_errors(sem_errors, sem_warnings)
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

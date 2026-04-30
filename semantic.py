"""
Phase 3 – Semantic Analysis.

Walks the AST and enforces:
  • Declaration before use
  • No redeclaration in the same scope
  • Type compatibility on assignments and expressions
  • Correct operand types for operators
  • Bool conditions in if / while

Maintains a hierarchical symbol table (scopes nest with blocks).
"""

from ast_nodes import *
from typing import Dict, List, Optional, Tuple, Any


# ══════════════════════════════════════════════════════════ symbol table ══════

class Symbol:
    def __init__(self, name: str, var_type: str, line: int) -> None:
        self.name     = name
        self.var_type = var_type
        self.line     = line

    def __repr__(self) -> str:
        return f"{self.name} : {self.var_type}  (line {self.line})"


class SymbolTable:
    def __init__(self, parent: Optional['SymbolTable'] = None) -> None:
        self.symbols:     Dict[str, Symbol] = {}
        self.parent:      Optional['SymbolTable'] = parent
        self.scope_level: int = (parent.scope_level + 1) if parent else 0

    def define(self, sym: Symbol) -> None:
        self.symbols[sym.name] = sym

    def lookup(self, name: str) -> Optional[Symbol]:
        if name in self.symbols:
            return self.symbols[name]
        return self.parent.lookup(name) if self.parent else None

    def lookup_local(self, name: str) -> Optional[Symbol]:
        return self.symbols.get(name)

    def all_symbols(self) -> Dict[str, Symbol]:
        result: Dict[str, Symbol] = {}
        if self.parent:
            result.update(self.parent.all_symbols())
        result.update(self.symbols)
        return result


# ═══════════════════════════════════════════════════════════ analyser ════════

class SemanticAnalyzer:
    # Types that can widen (e.g. int fits into float)
    _COMPAT: Dict[str, set] = {
        'int':    {'int'},
        'float':  {'float', 'int'},
        'string': {'string'},
        'bool':   {'bool'},
    }
    _ARITH  = {'+', '-', '*', '/', '%'}
    _CMP    = {'<', '>', '<=', '>=', '==', '!='}
    _LOGIC  = {'&&', '||'}
    _NUMERIC = {'int', 'float'}

    def __init__(self) -> None:
        self.global_scope  = SymbolTable()
        self.current_scope = self.global_scope
        self.errors:  List[str] = []
        self.warnings: List[str] = []
        self.log:     List[str] = []

    # ──────────────────────────────────────────────── public interface ────────

    def analyze(
        self, ast: Program
    ) -> Tuple[List[str], List[str], SymbolTable, List[str]]:
        """Return (errors, warnings, global_symbol_table, analysis_log)."""
        self._log("╔══════════════════════════════════════════╗")
        self._log("║         SEMANTIC ANALYSIS                ║")
        self._log("╚══════════════════════════════════════════╝")
        self._log("")
        self._visit_program(ast)
        return self.errors, self.warnings, self.global_scope, self.log

    # ──────────────────────────────────────────────── logging helpers ─────────

    def _log(self, msg: str) -> None:
        self.log.append(msg)

    def _err(self, msg: str) -> None:
        self.errors.append(msg)
        self.log.append(f"  [ERROR]   {msg}")

    def _warn(self, msg: str) -> None:
        self.warnings.append(msg)
        self.log.append(f"  [WARN]    {msg}")

    def _enter_scope(self) -> None:
        self.current_scope = SymbolTable(self.current_scope)
        self._log(f"  ──► enter scope (level {self.current_scope.scope_level})")

    def _exit_scope(self) -> None:
        self._log(f"  ◄── exit scope  (level {self.current_scope.scope_level})")
        self.current_scope = self.current_scope.parent

    # ──────────────────────────────────────────────── visitors ───────────────

    def _visit_program(self, node: Program) -> None:
        self._log("Checking: program")
        for stmt in node.statements:
            self._visit_stmt(stmt)

    def _visit_stmt(self, node: ASTNode) -> None:
        if isinstance(node, DeclStmt):
            self._visit_decl(node)
        elif isinstance(node, AssignStmt):
            self._visit_assign(node)
        elif isinstance(node, IfStmt):
            self._visit_if(node)
        elif isinstance(node, WhileStmt):
            self._visit_while(node)
        elif isinstance(node, PrintStmt):
            self._visit_print(node)
        elif isinstance(node, Block):
            self._visit_block(node)

    def _visit_decl(self, node: DeclStmt) -> None:
        self._log(f"  Checking decl: {node.var_type} {node.name}  (line {node.line})")
        if self.current_scope.lookup_local(node.name):
            self._err(
                f"Line {node.line}: Variable '{node.name}' already declared "
                f"in this scope"
            )
            return
        if node.initializer:
            init_type = self._expr_type(node.initializer)
            if init_type and not self._compatible(node.var_type, init_type):
                self._err(
                    f"Line {node.line}: Cannot assign {init_type} to "
                    f"{node.var_type} variable '{node.name}'"
                )
        sym = Symbol(node.name, node.var_type, node.line)
        self.current_scope.define(sym)
        self._log(f"    Defined  {node.name} : {node.var_type}")

    def _visit_assign(self, node: AssignStmt) -> None:
        self._log(f"  Checking assign: {node.name}  (line {node.line})")
        sym = self.current_scope.lookup(node.name)
        if not sym:
            self._err(f"Line {node.line}: Undefined variable '{node.name}'")
            return
        val_type = self._expr_type(node.value)
        if val_type and not self._compatible(sym.var_type, val_type):
            self._err(
                f"Line {node.line}: Cannot assign {val_type} to "
                f"{sym.var_type} variable '{node.name}'"
            )

    def _visit_if(self, node: IfStmt) -> None:
        self._log(f"  Checking if  (line {node.line})")
        cond_t = self._expr_type(node.condition)
        if cond_t and cond_t != 'bool':
            self._warn(
                f"Line {node.line}: if-condition is '{cond_t}', expected 'bool'"
            )
        self._visit_block(node.then_block)
        if node.else_block:
            self._visit_block(node.else_block)

    def _visit_while(self, node: WhileStmt) -> None:
        self._log(f"  Checking while  (line {node.line})")
        cond_t = self._expr_type(node.condition)
        if cond_t and cond_t != 'bool':
            self._warn(
                f"Line {node.line}: while-condition is '{cond_t}', expected 'bool'"
            )
        self._visit_block(node.body)

    def _visit_print(self, node: PrintStmt) -> None:
        self._log(f"  Checking print  (line {node.line})")
        self._expr_type(node.value)

    def _visit_block(self, node: Block) -> None:
        self._enter_scope()
        for stmt in node.statements:
            self._visit_stmt(stmt)
        self._exit_scope()

    # ──────────────────────────────────────────── type inference ─────────────

    def _expr_type(self, node: ASTNode) -> Optional[str]:
        if isinstance(node, NumberLiteral):
            return 'int' if node.is_int else 'float'

        if isinstance(node, StringLiteral):
            return 'string'

        if isinstance(node, BoolLiteral):
            return 'bool'

        if isinstance(node, Identifier):
            sym = self.current_scope.lookup(node.name)
            if not sym:
                self._err(f"Line {node.line}: Undefined variable '{node.name}'")
                return None
            return sym.var_type

        if isinstance(node, UnaryExpr):
            op_t = self._expr_type(node.operand)
            if node.op == '!':
                if op_t and op_t != 'bool':
                    self._err(f"Operator '!' requires bool, got '{op_t}'")
                return 'bool'
            if node.op == '-':
                if op_t and op_t not in self._NUMERIC:
                    self._err(f"Unary '-' requires numeric, got '{op_t}'")
                return op_t
            return op_t

        if isinstance(node, BinaryExpr):
            lt = self._expr_type(node.left)
            rt = self._expr_type(node.right)
            if lt is None or rt is None:
                return None
            op = node.op

            if op in self._ARITH:
                # Allow string + string (concatenation)
                if op == '+' and lt == 'string' and rt == 'string':
                    return 'string'
                if lt not in self._NUMERIC or rt not in self._NUMERIC:
                    self._err(
                        f"Operator '{op}' requires numeric operands, "
                        f"got '{lt}' and '{rt}'"
                    )
                    return None
                return 'float' if 'float' in (lt, rt) else 'int'

            if op in self._CMP:
                if lt != rt and not (lt in self._NUMERIC and rt in self._NUMERIC):
                    self._err(f"Cannot compare '{lt}' with '{rt}'")
                return 'bool'

            if op in self._LOGIC:
                if lt != 'bool' or rt != 'bool':
                    self._warn(
                        f"Operator '{op}' expects bool operands, "
                        f"got '{lt}' and '{rt}'"
                    )
                return 'bool'

        return None

    def _compatible(self, target: str, source: str) -> bool:
        return source in self._COMPAT.get(target, set())

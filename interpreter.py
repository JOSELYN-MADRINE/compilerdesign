"""
Phase 4 – Tree-Walking Interpreter.

Walks the AST produced by either parser and executes the program.
Maintains a runtime Environment (scope chain) that mirrors the block
structure, and collects all print() output into a list of strings.
"""

from ast_nodes import *
from typing import Any, List, Optional


class RuntimeError(Exception):
    pass


# ══════════════════════════════════════════════════════ runtime environment ══

class Environment:
    """Scope-chained variable store."""

    def __init__(self, parent: Optional['Environment'] = None) -> None:
        self._store: dict  = {}
        self.parent        = parent

    def define(self, name: str, value: Any) -> None:
        self._store[name] = value

    def get(self, name: str) -> Any:
        if name in self._store:
            return self._store[name]
        if self.parent:
            return self.parent.get(name)
        raise RuntimeError(f"Undefined variable '{name}'")

    def assign(self, name: str, value: Any) -> None:
        if name in self._store:
            self._store[name] = value
            return
        if self.parent:
            self.parent.assign(name, value)
            return
        raise RuntimeError(f"Undefined variable '{name}'")


# ══════════════════════════════════════════════════════════════ interpreter ══

_MAX_ITERATIONS = 100_000   # infinite-loop guard


class Interpreter:
    def __init__(self) -> None:
        self.output:   List[str] = []   # lines from print()
        self.errors:   List[str] = []
        self.exe_log:  List[str] = []   # execution trace (brief)
        self.env = Environment()

    # ─────────────────────────────────────────────── public entry point ───────

    def run(self, ast: Program):
        self.exe_log.append("╔══════════════════════════════════════════╗")
        self.exe_log.append("║         PROGRAM EXECUTION                ║")
        self.exe_log.append("╚══════════════════════════════════════════╝")
        self.exe_log.append("")
        try:
            self._exec_program(ast)
            self.exe_log.append("")
            self.exe_log.append(f"Execution finished.  {len(self.output)} line(s) of output.")
        except RuntimeError as exc:
            self.errors.append(str(exc))
            self.exe_log.append(f"[RUNTIME ERROR]  {exc}")
        return self.output, self.errors, self.exe_log

    # ─────────────────────────────────────────────── statement executors ──────

    def _exec_program(self, node: Program) -> None:
        for stmt in node.statements:
            self._exec(stmt)

    def _exec(self, node: ASTNode) -> None:
        if isinstance(node, DeclStmt):
            self._exec_decl(node)
        elif isinstance(node, AssignStmt):
            self._exec_assign(node)
        elif isinstance(node, IfStmt):
            self._exec_if(node)
        elif isinstance(node, WhileStmt):
            self._exec_while(node)
        elif isinstance(node, PrintStmt):
            self._exec_print(node)
        elif isinstance(node, Block):
            self._exec_block(node, new_scope=True)

    def _exec_decl(self, node: DeclStmt) -> None:
        if node.initializer:
            val = self._eval(node.initializer)
            val = self._coerce(val, node.var_type, node.line)
        else:
            val = {'int': 0, 'float': 0.0, 'string': '', 'bool': False}.get(node.var_type, None)
        self.env.define(node.name, val)
        self.exe_log.append(f"  decl  {node.name} = {_fmt(val)}")

    def _exec_assign(self, node: AssignStmt) -> None:
        val = self._eval(node.value)
        self.env.assign(node.name, val)
        self.exe_log.append(f"  assign  {node.name} = {_fmt(val)}")

    def _exec_if(self, node: IfStmt) -> None:
        cond = self._eval(node.condition)
        if _truthy(cond):
            self.exe_log.append(f"  if  condition = {_fmt(cond)}  → THEN branch")
            self._exec_block(node.then_block, new_scope=True)
        else:
            self.exe_log.append(f"  if  condition = {_fmt(cond)}  → ELSE branch")
            if node.else_block:
                self._exec_block(node.else_block, new_scope=True)

    def _exec_while(self, node: WhileStmt) -> None:
        iterations = 0
        self.exe_log.append("  while  loop start")
        while True:
            cond = self._eval(node.condition)
            if not _truthy(cond):
                self.exe_log.append(f"  while  condition = {_fmt(cond)}  → exit  ({iterations} iterations)")
                break
            iterations += 1
            if iterations > _MAX_ITERATIONS:
                raise RuntimeError(
                    f"Infinite loop detected — exceeded {_MAX_ITERATIONS} iterations"
                )
            self._exec_block(node.body, new_scope=True)

    def _exec_print(self, node: PrintStmt) -> None:
        val = self._eval(node.value)
        out = _fmt(val)
        self.output.append(out)
        self.exe_log.append(f"  print → {out}")

    def _exec_block(self, node: Block, new_scope: bool = False) -> None:
        if new_scope:
            saved = self.env
            self.env = Environment(parent=saved)
            try:
                for stmt in node.statements:
                    self._exec(stmt)
            finally:
                self.env = saved
        else:
            for stmt in node.statements:
                self._exec(stmt)

    # ─────────────────────────────────────────────── expression evaluator ─────

    def _eval(self, node: ASTNode) -> Any:
        if isinstance(node, NumberLiteral):
            return node.value

        if isinstance(node, StringLiteral):
            return node.value

        if isinstance(node, BoolLiteral):
            return node.value

        if isinstance(node, Identifier):
            return self.env.get(node.name)

        if isinstance(node, UnaryExpr):
            val = self._eval(node.operand)
            if node.op == '-':
                return -val
            if node.op == '!':
                return not _truthy(val)

        if isinstance(node, BinaryExpr):
            return self._eval_binary(node)

        return None

    def _eval_binary(self, node: BinaryExpr) -> Any:
        op = node.op

        # Short-circuit logical operators
        if op == '&&':
            return _truthy(self._eval(node.left)) and _truthy(self._eval(node.right))
        if op == '||':
            return _truthy(self._eval(node.left)) or _truthy(self._eval(node.right))

        left  = self._eval(node.left)
        right = self._eval(node.right)

        if op == '+':
            if isinstance(left, str) or isinstance(right, str):
                return str(left) + str(right)
            return left + right
        if op == '-':  return left - right
        if op == '*':  return left * right
        if op == '/':
            if right == 0:
                raise RuntimeError("Division by zero")
            result = left / right
            return int(result) if isinstance(left, int) and isinstance(right, int) and result == int(result) else result
        if op == '%':
            if right == 0:
                raise RuntimeError("Modulo by zero")
            return left % right
        if op == '==': return left == right
        if op == '!=': return left != right
        if op == '<':  return left < right
        if op == '>':  return left > right
        if op == '<=': return left <= right
        if op == '>=': return left >= right
        return None

    def _coerce(self, val: Any, target: str, line: int) -> Any:
        try:
            if target == 'int':    return int(val)
            if target == 'float':  return float(val)
            if target == 'string': return str(val)
            if target == 'bool':   return bool(val)
        except (ValueError, TypeError):
            raise RuntimeError(f"Line {line}: Cannot convert {val!r} to {target}")
        return val


# ─────────────────────────────────────────────────── small utilities ──────────

def _truthy(val: Any) -> bool:
    if isinstance(val, bool):   return val
    if isinstance(val, (int, float)): return val != 0
    if isinstance(val, str):    return len(val) > 0
    return bool(val)


def _fmt(val: Any) -> str:
    if isinstance(val, bool):  return 'true' if val else 'false'
    if isinstance(val, float):
        # Print whole-number floats without trailing .0 clutter
        return str(int(val)) if val == int(val) else str(val)
    return str(val)

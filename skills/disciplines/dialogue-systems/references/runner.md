# A custom dialogue runner

Contents:
1. Graph schema
2. Variable store and sandboxed expression evaluation (`evaluate`)
3. The runner state machine (`DialogueRunner`)
4. Localization lookup (`make_localizer`)
5. Validation pass (`validate_graph`)

When Ink/Yarn are more than you need, a small data-driven runner is enough for
lines, choices, conditions, and variable writes. Build a **graph interpreter**,
not a language. The Python below is engine-neutral and runs as written.

## Graph schema

```json
{
  "start": "node_id",
  "vars":  { "gold": 0, "met_guard": false },
  "nodes": {
    "<id>": {
      "speaker": "Guard",              // optional
      "line":    "DLG_KEY",            // localization key (or raw text in a pinch)
      "set":     { "var": "expr" },    // optional: assignments applied on entry/transition
      "choices": [                       // optional: branch point
        { "text": "OPT_KEY", "to": "<id>", "if": "expr", "set": { } }
      ],
      "next":    "<id>",               // optional: linear auto-advance
      "end":     true                  // optional: terminate the conversation
    }
  }
}
```

Exactly one of `choices`, `next`, or `end` should determine where a node goes.

## Variable store and expression evaluation

Keep variables in a flat dict. Evaluate conditions/assignments with a **tiny,
sandboxed** expression evaluator — never `eval()` untrusted strings in a way that
exposes the host language.

```python
import ast, operator as op

_BIN = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
        ast.Mod: op.mod}
_CMP = {ast.Eq: op.eq, ast.NotEq: op.ne, ast.Lt: op.lt, ast.LtE: op.le,
        ast.Gt: op.gt, ast.GtE: op.ge}
_BOOL = {ast.And: all, ast.Or: any}

def evaluate(expr, vars):
    """Safely evaluate a boolean/arithmetic expression over the variable store."""
    if expr is None or expr == "":
        return True
    def ev(node):
        if isinstance(node, ast.Expression):  return ev(node.body)
        if isinstance(node, ast.Constant):    return node.value
        if isinstance(node, ast.Name):        return vars[node.id]  # KeyError names a typo
        if isinstance(node, ast.BoolOp):      return _BOOL[type(node.op)](ev(v) for v in node.values)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not ev(node.operand)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -ev(node.operand)              # negative literals: "rep > -5"
        if isinstance(node, ast.BinOp):       return _BIN[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.Compare):
            left = ev(node.left); res = True
            for o, c in zip(node.ops, node.comparators):
                right = ev(c); res = res and _CMP[type(o)](left, right); left = right
            return res
        raise ValueError("unsupported expression")
    return ev(ast.parse(expr, mode="eval"))
```

This whitelists only names, literals, arithmetic, comparison, and boolean ops —
it cannot call functions or touch the host environment. The syntax is Python's, so
booleans are `True`/`False`, logic is `and`/`or`/`not`, and a string literal needs
inner quotes (`"mood == 'angry'"`). An unknown name raises `KeyError` instead of
quietly comparing `None`, which would itself raise `TypeError` on `<`/`>`. (Engines
without a safe parser should ship a hand-written tokenizer instead of exposing a real
`eval`.)

## The runner state machine

```python
class DialogueRunner:
    def __init__(self, graph, ui, localize):
        self.graph, self.ui, self.localize = graph, ui, localize
        self.vars = dict(graph.get("vars", {}))
        self.current = None

    def start(self):
        self._goto(self.graph["start"])

    def _apply_set(self, sets):
        # Evaluate each RHS against the CURRENT vars, then commit (snapshot first
        # so 'a: b' and 'b: a' in one block don't see each other's new values).
        updates = {k: evaluate(v, self.vars) if isinstance(v, str) else v
                   for k, v in sets.items()}
        self.vars.update(updates)

    def _goto(self, node_id):
        node = self.graph["nodes"][node_id]
        self.current = node
        self._apply_set(node.get("set", {}))
        if node.get("end"):
            self.ui.close(); return
        if "line" in node:
            self.ui.show_line(node.get("speaker", ""), self.localize(node["line"]))
        if "choices" in node:
            shown = [c for c in node["choices"] if evaluate(c.get("if"), self.vars)]
            self.ui.show_choices(shown)            # UI calls choose() with one of these
        elif "next" in node:
            self.ui.show_continue(lambda: self._goto(node["next"]))

    def choose(self, choice):
        self._apply_set(choice.get("set", {}))     # write on the transition (revisit-safe)
        self._goto(choice["to"])
```

## Localization lookup

```python
def make_localizer(tables, locale, fallback="en"):
    table = tables.get(locale, {})
    base  = tables.get(fallback, {})
    def localize(key):
        return table.get(key, base.get(key, f"<MISSING:{key}>"))  # never crash on a gap
    return localize
```

Ship one table per locale keyed by line ID. A missing key returns a visible
placeholder rather than failing — easy to spot in QA.

## Validation pass

Run this on every dialogue file in CI or before handing work back. It returns a list of
problems; an empty list means every target exists, every node terminates, every expression
parses and names only declared variables, and every node is reachable from `start`.

```python
def validate_graph(graph):
    problems = []
    nodes, declared = graph.get("nodes", {}), set(graph.get("vars", {}))

    def check_expr(where, expr):
        if not isinstance(expr, str) or expr == "":
            return
        try:
            tree = ast.parse(expr, mode="eval")
        except SyntaxError as exc:
            problems.append(f"{where}: cannot parse {expr!r}: {exc.msg}")
            return
        for name in {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} - declared:
            problems.append(f"{where}: undeclared variable {name!r}")

    def check_sets(where, sets):
        for var, expr in sets.items():
            if var not in declared:
                problems.append(f"{where}: sets undeclared variable {var!r}")
            check_expr(f"{where} set {var}", expr)

    if graph.get("start") not in nodes:
        problems.append(f"start node {graph.get('start')!r} does not exist")
    for node_id, node in nodes.items():
        exits = [k for k in ("choices", "next", "end") if node.get(k)]
        if len(exits) != 1:
            problems.append(f"{node_id}: needs exactly one of choices/next/end, has {exits or 'none'}")
        check_sets(node_id, node.get("set", {}))
        if node.get("next") and node["next"] not in nodes:
            problems.append(f"{node_id}: next {node['next']!r} does not exist")
        for i, choice in enumerate(node.get("choices", [])):
            where = f"{node_id} choice {i}"
            if choice.get("to") not in nodes:
                problems.append(f"{where}: target {choice.get('to')!r} does not exist")
            check_expr(f"{where} if", choice.get("if"))
            check_sets(where, choice.get("set", {}))

    seen, stack = set(), [graph.get("start")]
    while stack:
        node_id = stack.pop()
        if node_id in seen or node_id not in nodes:
            continue
        seen.add(node_id)
        node = nodes[node_id]
        stack += [c.get("to") for c in node.get("choices", [])] + [node.get("next")]
    problems += [f"{node_id}: unreachable from start" for node_id in nodes if node_id not in seen]
    return problems
```

Print the problems and exit non-zero when the list is not empty, so CI fails. These checks catch the dead ends and typos that otherwise strand the player mid-scene.

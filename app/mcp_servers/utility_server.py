import ast
import operator

from datetime import datetime, timezone
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("safe-utility-tools")


@mcp.tool()
def current_utc_time() -> str:
    """Return the current UTC timestamp."""

    return datetime.now(timezone.utc).isoformat()


@mcp.tool()
def safe_calculate(expression: str) -> str:
    """Calculate basic arithmetic without evaluating arbitrary code."""

    operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.Mod: operator.mod,
    }

    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)

        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, (int, float))
        ):
            return node.value

        if (
            isinstance(node, ast.BinOp)
            and type(node.op) in operators
        ):
            left = visit(node.left)
            right = visit(node.right)

            if isinstance(node.op, ast.Pow) and abs(right) > 8:
                raise ValueError("Exponent too large")

            result = operators[type(node.op)](left, right)

            if abs(float(result)) > 1e100:
                raise ValueError("Result too large")

            return result

        if (
            isinstance(node, ast.UnaryOp)
            and type(node.op) in operators
        ):
            return operators[type(node.op)](
                visit(node.operand)
            )

        raise ValueError(
            "Only simple arithmetic is allowed"
        )

    try:
        tree = ast.parse(expression, mode="eval")
        return str(visit(tree))

    except Exception as error:
        return f"Rejected: {error}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
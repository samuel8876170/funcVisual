import streamlit as st
from sympy import symbols, sympify, lambdify
import numpy as np
import pandas as pd
from scipy.optimize import brentq
import plotly.express as px
import re

#   Sidebar for definitions
st.sidebar.title("Definitions")
definitions = st.sidebar.text_area("Enter definitions here, one per line:", height=300)

#   Instructions
st.sidebar.markdown("""
### Instructions
- Define functions as `name: y = expression`
    - e.g., `A: x + 2`
- Functions can reference other functions
    - e.g. `B: 2*A + 3*x^2`
- Functions can be conditional,
    - e.g. `C: {0 if x < 0.5, x-0.5 otherwise}-5.5`
- Functions can be aggregated
    - e.g. `D: A - {0 if x < 3, x-3 otherwise}+3.5`
""")


def syntax_check(s: str) -> bool:
    """Check all functions' syntax"""
    if s.count(":") != 1:
        st.error(f'Non-unique Assignment ":" - {s}')
        return False
    condc = s.count("{") + s.count("}")
    if condc % 2 == 1:
        st.error(
            f"Conditional expression is not well defined inside brackets {{}} - {s}"
        )
        return False
    if s.count("otherwise") != condc // 2:
        st.error(
            f'Every conditional expression should have "otherwise" term at the end - {s}'
        )
        return False
    return True


#   Split and Extact each line
split_re = re.compile(r"([^\n]*):([^\n]*)")
clean_re = re.compile(r" *:* *")
cond_re = re.compile(r"\{([^}]*)\}")
chaineq_re = re.compile(
    r"(-?\d*\.?\d+)\s*(>=|>|<|<=)\s*([a-zA-Z]+)\s*(>=|>|<|<=)\s*(-?\d*\.?\d+)"
)
lines = [s.strip() for s in definitions.split("\n") if s.strip()]
func_dict = {
    clean_re.sub("", name): expr.replace(" ", "")
    for name, expr in map(
        lambda x: split_re.match(x).group(1, 2), filter(syntax_check, lines)
    )
}


def translate_conditional(expr: str) -> str:
    """Translate user conditional expr to sympy Piecewise"""
    m = cond_re.finditer(expr)
    if not m:
        return expr
    for g in map(lambda x: x.group(), m):
        expr = expr.replace(
            g,
            "Piecewise("
            + ",".join(
                map(
                    lambda x: f"({x.replace('if', ',').replace('otherwise', ',True')})",
                    g[1:-1].split(","),
                )
            )
            + ")",
        )
    return chaineq_re.sub(r"\1 \2 \3 & \3 \4 \5", expr)


func_dict = dict(
    map(lambda kv: (kv[0], translate_conditional(kv[1])), func_dict.items())
)


def deref_func(d: dict, expr: str) -> str:
    """Dereference all the dependency chain of functions"""
    r = expr
    for fn in d:
        if fn in r:
            r = r.replace(fn, f"({d[fn]})")
    return r


for _ in range(1000):
    new_func_dict = dict(
        map(lambda kv: (kv[0], deref_func(func_dict, kv[1])), func_dict.items())
    )
    if new_func_dict == func_dict:
        break
    func_dict = new_func_dict
else:
    st.error("Stack Overflow when dereferencing functions")


#   Parse expression into lambda function
x = symbols("x")
lambda_dict = {}
for fn, expr in func_dict.items():
    try:
        lambda_dict[fn] = lambdify(x, sympify(expr), modules=["numpy"])
    except Exception as e:
        st.error(f"Unable to parse function {fn}:{expr} - {e}")


#   Plot graph
x_min = st.sidebar.number_input("X-axis minimum", value=-10.0)
x_max = st.sidebar.number_input("X-axis maximum", value=10.0)
x_step = int(1000 * np.log10(x_max - x_min))
if x_min >= x_max:
    st.error("X-axis minimum must be less than X-axis maximum")
    x_min, x_max = (-10.0, 10.0)
fig = px.line()
x_grid = np.linspace(x_min, x_max, x_step)
try:
    for fn, f in lambda_dict.items():
        fig.add_scatter(x=x_grid, y=f(x_grid), name=fn)
except Exception as e:
    st.error(f"Error plotting functions: {e}")

st.plotly_chart(fig, use_container_width=True)


#   Calculate all intersections to X/Y-axis
def find_roots(f, a, b, num_points=1000):
    x_grid = np.linspace(a, b, num_points)
    y_grid = f(x_grid)
    roots = []
    for i in range(len(x_grid) - 1):
        if y_grid[i] == 0:
            roots.append(x_grid[i])
        elif y_grid[i] * y_grid[i + 1] < 0:
            try:
                root = brentq(f, x_grid[i], x_grid[i + 1])
                roots.append(root)
            except ValueError:
                pass  # No root in this interval
    if y_grid[-1] == 0:
        roots.append(x_grid[-1])
    return sorted(set(roots))  # Remove duplicates and sort


st.subheader("Intercepts")
for fn in lambda_dict:
    st.write(f"#### Function {fn}")
    st.write("**Y - intercepts**")
    try:
        y_intercept = lambda_dict[fn](0)
        st.write(pd.DataFrame({"x": [0], "y": [y_intercept]}))
    except Exception:
        st.write("Y-intercept: Cannot compute (possibly undefined at x=0)")

    # X-intercepts: roots within [x_min, x_max]
    roots = find_roots(lambda_dict[fn], x_min, x_max, x_step)
    st.write("**X - intercepts**")
    if roots:
        st.write(pd.DataFrame({"x": roots, "y": [0] * len(roots)}))
    else:
        st.write("None in the given range")

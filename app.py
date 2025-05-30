from math import log
import streamlit as st
from sympy import symbols, sympify, lambdify
import numpy as np
from scipy import stats
import plotly.express as px
import re

# Sidebar for definitions
st.sidebar.title("Definitions")
definitions = st.sidebar.text_area("Enter definitions here, one per line:", height=300)

# Instructions
st.sidebar.markdown("""
### Instructions
- Define functions as `name: y = expression`, e.g., `A: y = x + 2`
- For conditional functions, use SymPy's Piecewise, e.g., `B: y = Piecewise((x+2, x<2), (2*x, True))`
- Define random variables as `name: distribution(params)`, e.g., `N: Normal(0.5, 0.79)`
- Supported distributions: Normal(mean, std), Uniform(a, b)
- If you define `x: distribution(params)`, functions are plotted as points using samples of x
""")


def syntax_check(s: str) -> bool:
    if s.count(":") != 1:
        st.error(f'Non-unique Assignment ":" - {s}')
        return False
    if s.count("=") != 1:
        st.error(f'Non-unique Formula Operation "=" - {s}')
        return False
    return True


# 1. Split and Extact each line
split_re = re.compile(r"(.*:)([^:]\D*=)([^=].*)")
clean_re = re.compile(r" *:* *")
lines = [s.strip() for s in definitions.split("\n") if s.strip()]
func_dict = {
    clean_re.sub("", name): expr.replace(" ", "")
    for name, expr in map(
        lambda x: split_re.match(x).group(1, 3), filter(syntax_check, lines)
    )
}


# 2. Dereference all the dependency chain of functions
def deref_func(d: dict, expr: str) -> str:
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

# 3. Parse expression into lambda function
x = symbols("x")
lambda_dict = {}
for fn, expr in func_dict.items():
    try:
        lambda_dict[fn] = lambdify(x, sympify(expr), modules=["numpy"])
    except Exception as e:
        st.error(f"Unable to parse function {fn}:{expr} - {e}")


# 4. Plot graph
x_min = st.sidebar.number_input("X-axis minimum", value=-10.0)
x_max = st.sidebar.number_input("X-axis maximum", value=10.0)
if x_min >= x_max:
    st.error("X-axis minimum must be less than X-axis maximum")
    x_min, x_max = (-10.0, 10.0)
fig = px.line(title="Function Plots")
x_grid = np.linspace(x_min, x_max, int(1000 * np.log10(x_max - x_min)))
try:
    for fn, f in lambda_dict.items():
        fig.add_scatter(x=x_grid, y=f(x_grid), name=fn)
except Exception as e:
    st.error(f"Error plotting functions: {e}")

st.plotly_chart(fig, use_container_width=True)

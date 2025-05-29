import streamlit as st
from sympy import *
import numpy as np
from scipy import stats
import plotly.express as px

# Initialize session state
if "samples" not in st.session_state:
    st.session_state.samples = {}
if "x_samples" not in st.session_state:
    st.session_state.x_samples = None

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

# Parse definitions
lines = [line.strip() for line in definitions.split("\n") if line.strip()]
random_vars = {}
functions = {}
dist_map = {
    "Normal": {"func": stats.norm, "params": ["mean", "std"]},
    "Uniform": {"func": stats.uniform, "params": ["a", "b"]},
}

for line in lines:
    if ":" not in line:
        continue
    name, definition = [part.strip() for part in line.split(":", 1)]
    if "y =" in definition:
        # Function definition
        expr_str = definition.split("y =", 1)[1].strip()
        # Substitute references to other functions
        for func_name in functions:
            if func_name in expr_str:
                expr_str = expr_str.replace(func_name, f"({str(functions[func_name])})")
        # Parse with SymPy
        symbols_list = ["x"] + list(random_vars.keys())
        syms = symbols(symbols_list)
        try:
            expr = sympify(
                expr_str, locals={s: syms[symbols_list.index(s)] for s in symbols_list}
            )
            functions[name] = expr
        except Exception as e:
            st.error(f"Error parsing function {name}: {e}")
    else:
        # Random variable definition
        try:
            dist_name = definition.split("(")[0].strip()
            params_str = definition.split("(")[1].split(")")[0]
            params = [float(p.strip()) for p in params_str.split(",")]
            if dist_name in dist_map:
                random_vars[name] = (dist_name, params)
            else:
                st.error(f"Unsupported distribution: {dist_name}")
        except Exception as e:
            st.error(f"Error parsing random variable {name}: {e}")

# Roll button
roll = st.button("Roll")

# Sample random variables
if roll:
    st.session_state.samples = {}
    st.session_state.x_samples = None
    for name in random_vars:
        dist_name, params = random_vars[name]
        if dist_name == "Normal":
            mu, sigma = params
            st.session_state.samples[name] = np.random.normal(mu, sigma)
        elif dist_name == "Uniform":
            a, b = params
            st.session_state.samples[name] = np.random.uniform(a, b)
    if "x" in random_vars:
        dist_name, params = random_vars["x"]
        if dist_name == "Normal":
            mu, sigma = params
            st.session_state.x_samples = np.random.normal(mu, sigma, size=100)
        elif dist_name == "Uniform":
            a, b = params
            st.session_state.x_samples = np.random.uniform(a, b, size=100)
else:
    for name in random_vars:
        if name not in st.session_state.samples:
            dist_name, params = random_vars[name]
            if dist_name == "Normal":
                mu, sigma = params
                st.session_state.samples[name] = np.random.normal(mu, sigma)
            elif dist_name == "Uniform":
                a, b = params
                st.session_state.samples[name] = np.random.uniform(a, b)
    if "x" in random_vars and st.session_state.x_samples is None:
        dist_name, params = random_vars["x"]
        if dist_name == "Normal":
            mu, sigma = params
            st.session_state.x_samples = np.random.normal(mu, sigma, size=100)
        elif dist_name == "Uniform":
            a, b = params
            st.session_state.x_samples = np.random.uniform(a, b, size=100)

# Plotting
fig = px.line(title="Function Plots")
if "x" not in random_vars:
    # Standard mode: plot curves
    x_grid = np.linspace(-10, 10, 1000)
    for name, expr in functions.items():
        try:
            subs_dict = {
                sym: st.session_state.samples[str(sym)]
                for sym in expr.free_symbols
                if str(sym) in st.session_state.samples
            }
            expr_sub = expr.subs(subs_dict)
            f = lambdify(x, expr_sub, modules=["numpy"])
            y_values = f(x_grid)
            fig.add_scatter(x=x_grid, y=y_values, name=name)
        except Exception as e:
            st.error(f"Error plotting function {name}: {e}")
else:
    # Random mode: plot points
    x_samples = st.session_state.x_samples
    for name, expr in functions.items():
        try:
            subs_dict = {
                sym: st.session_state.samples[str(sym)]
                for sym in expr.free_symbols
                if str(sym) in st.session_state.samples and str(sym) != "x"
            }
            expr_sub = expr.subs(subs_dict)
            y_values = [float(expr_sub.subs(x, xi)) for xi in x_samples]
            fig.add_scatter(x=x_samples, y=y_values, mode="markers", name=name)
        except Exception as e:
            st.error(f"Error plotting function {name}: {e}")

st.plotly_chart(fig, use_container_width=True)

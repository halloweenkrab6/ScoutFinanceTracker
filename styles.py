import streamlit as st

def apply_custom_styles():
    st.markdown("""
        <style>
        .main {
            padding: 2rem;
        }
        .stButton>button {
            background-color: #003f87;
            color: white;
            border-radius: 4px;
            padding: 0.5rem 1rem;
        }
        .stButton>button:hover {
            background-color: #002a5c;
        }
        .css-qrbaxs {
            font-size: 28px;
            color: #003f87;
        }
        .stDataFrame {
            border: 1px solid #e6e6e6;
            border-radius: 4px;
        }
        .row-widget.stRadio > div {
            flex-direction: row;
            gap: 1rem;
        }
        </style>
    """, unsafe_allow_html=True)

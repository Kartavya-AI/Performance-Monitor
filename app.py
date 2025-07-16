# app.py
import streamlit as st
import os
import json
import pandas as pd
from src.performance_monitor.crew import PerformanceMonitorCrew

st.set_page_config(
    page_title="Performance Monitor Analysis",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Base & Font */
    body, .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #FFFFFF;
    }
    [data-testid="stSidebar"] .st-emotion-cache-17l2y9k { /* Sidebar title */
        color: #58a6ff;
    }

    /* Main Content Headers */
    h1, h2, h3 {
        color: #FFFFFF;
    }

    /* Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    div[data-testid="stMetric"] > div:nth-child(1) { /* Metric Label */
        color: #8b949e;
    }
    div[data-testid="stMetric"] > div:nth-child(2) { /* Metric Value */
        color: #c9d1d9;
    }

    /* Buttons */
    div[data-testid="stButton"] > button {
        border-radius: 8px;
        background-color: #238636;
        color: white;
        border: 1px solid #2ea043;
    }
    div[data-testid="stButton"] > button:hover {
        background-color: #2ea043;
        border-color: #3fb950;
    }
    
    /* Input widgets */
    div[data-testid="stTextInput"] > div > div > input, 
    div[data-testid="stSelectbox"] > div > div {
        background-color: #0d1117;
        color: #c9d1d9;
        border-color: #30363d;
    }

    /* Recommendation/Info Boxes */
    .recommendation-box {
        padding: 15px;
        border-radius: 8px;
        background-color: rgba(56, 139, 253, 0.1);
        border-left: 5px solid #388bfd;
        margin-bottom: 1rem;
        color: #c9d1d9;
    }

    /* Tabs */
    button[data-baseweb="tab"] {
        background-color: #161b22;
        color: #8b949e;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: #0d1117;
        color: #c9d1d9;
        border-bottom-color: #388bfd !important;
    }
    
    /* Dataframe */
    .stDataFrame {
        border: 1px solid #30363d;
        border-radius: 10px;
    }
    .stDataFrame > div:nth-child(1) {
        background-color: #161b22;
    }
    .stDataFrame .col_heading {
        background-color: #161b22 !important;
        color: #c9d1d9;
    }

</style>
""", unsafe_allow_html=True)

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "running" not in st.session_state:
    st.session_state.running = False

with st.sidebar:
    st.title("Performance Monitor Analysis")
    st.markdown("An AI crew to audit your website's performance, SEO, and accessibility.")
    st.markdown("---")
    
    st.subheader("API Configuration")
    
    llm_provider = st.selectbox(
        "Choose LLM Provider",
        ["Google Gemini", "OpenAI GPT"],
        help="Select your preferred AI model provider"
    )
    
    if llm_provider == "Google Gemini":
        llm_api_key = st.text_input("Gemini API Key", type="password", help="Get your API key from Google AI Studio")
        model_name = st.selectbox("Gemini Model", ["gemini-1.5-pro", "gemini-1.5-flash"], index=0)
    else:
        llm_api_key = st.text_input("OpenAI API Key", type="password", help="Your OpenAI API key")
        model_name = st.selectbox("OpenAI Model", ["gpt-4o", "gpt-4o-mini", "gpt-4"], index=0)
    
    # Serper API key is available for all LLM providers
    serper_api_key = st.text_input("Serper API Key (Optional)", type="password", help="For enhanced web search capabilities. Get from serper.dev")
    
    st.markdown("---")
    st.subheader("Website Analysis")
    url_to_analyze = st.text_input("Website URL to Analyze", "https://www.crewai.com/")
    
    if st.button("🚀 Analyze Website", disabled=st.session_state.running):
        if not llm_api_key:
            st.error(f"Please enter your {llm_provider} API key.")
        elif not url_to_analyze:
            st.error("Please enter a URL to analyze.")
        else:
            st.session_state.running = True
            st.session_state.analysis_result = None
            
            if llm_provider == "Google Gemini":
                os.environ["GOOGLE_API_KEY"] = llm_api_key
                os.environ["LLM_PROVIDER"] = "gemini"
                os.environ["GEMINI_MODEL_NAME"] = model_name
            else:
                os.environ["OPENAI_API_KEY"] = llm_api_key
                os.environ["LLM_PROVIDER"] = "openai"
                os.environ["OPENAI_MODEL_NAME"] = model_name
            
            # Now serper_api_key is always defined
            if serper_api_key:
                os.environ["SERPER_API_KEY"] = serper_api_key
            
            with st.spinner("The AI Crew is on the job... This may take a few minutes."):
                try:
                    crew_runner = PerformanceMonitorCrew(url=url_to_analyze)
                    result = crew_runner.run()
                    
                    if isinstance(result, str):
                        clean_result = result.strip().replace("```json", "").replace("```", "")
                        try:
                            st.session_state.analysis_result = json.loads(clean_result)
                        except json.JSONDecodeError:
                            import re
                            json_match = re.search(r'\{.*\}', clean_result, re.DOTALL)
                            if json_match:
                                st.session_state.analysis_result = json.loads(json_match.group())
                            else:
                                st.session_state.analysis_result = {"error": "Could not parse analysis result", "raw_result": clean_result}
                    else:
                        st.session_state.analysis_result = result
                        
                    st.session_state.running = False
                    st.success("Analysis completed successfully!")
                except Exception as e:
                    st.error(f"An error occurred: {e}", icon="🔥")
                    st.session_state.running = False
            st.rerun()

st.header("Performance Monitor Analysis Dashboard")
st.markdown(f"**Analysis Results for:** `{url_to_analyze}`")
st.markdown("---")

if st.session_state.analysis_result:
    data = st.session_state.analysis_result

    if "error" in data:
        st.error(f"Analysis Error: {data['error']}")
        if "raw_result" in data:
            st.text_area("Raw Result", data["raw_result"], height=200)
    else:
        kpis = data.get("kpis", {})
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("📄 Pages Scanned", kpis.get("pages_scanned", "N/A"))
        col2.metric("⏱️ Avg. Load (ms)", kpis.get("avg_load_time", "N/A"))
        col3.metric("🔗 Broken Links", kpis.get("broken_links", "N/A"))
        col4.metric("📈 SEO Issues", kpis.get("seo_issues", "N/A"))
        col5.metric("♿ Accessib. Errors", kpis.get("accessibility_errors", "N/A"))

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<h3>Key Insights & Actions</h3>", unsafe_allow_html=True)
        col1, col2 = st.columns([2, 3])
        with col1:
            with st.container(border=True):
                st.markdown("**📝 Overall Summary**")
                st.write(data.get("summary", "No summary provided."))
        with col2:
            with st.container(border=True):
                st.markdown("**🎯 Actionable Recommendations**")
                recommendations = data.get("recommendations", [])
                if recommendations:
                    for rec in recommendations:
                        st.markdown(f"<div class='recommendation-box'>{rec}</div>", unsafe_allow_html=True)
                else:
                    st.info("No specific recommendations available.")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<h3>📋 Detailed Analysis Data</h3>", unsafe_allow_html=True)
        tab1, tab2, tab3 = st.tabs(["Performance", "SEO", "Accessibility"])

        with tab1:
            perf_data = data.get("performance_details", [])
            if perf_data:
                st.dataframe(pd.DataFrame(perf_data), use_container_width=True)
            else:
                st.info("No performance data available.")
                
        with tab2:
            seo_data = data.get("seo_details", [])
            if seo_data:
                st.dataframe(pd.DataFrame(seo_data), use_container_width=True)
            else:
                st.info("No SEO data available.")
                
        with tab3:
            acc_data = data.get("accessibility_details", [])
            if acc_data:
                st.dataframe(pd.DataFrame(acc_data), use_container_width=True)
            else:
                st.info("No accessibility data available.")

elif st.session_state.running:
    st.info("Analysis is in progress. Please wait for the AI crew to complete their tasks...", icon="⏳")
    
else:
    st.info("Configure your API keys and enter a website URL in the sidebar, then click 'Analyze Website' to begin.", icon="👈")
import streamlit as st
import requests
from pathlib import Path
import json
import os
import webbrowser
from typing import Optional

# Configure page settings
st.set_page_config(
    page_title="LLM PDF Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Backend URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Initialize session state
if "selected_model" not in st.session_state:
    st.session_state.selected_model = "gpt-4"
if "api_response" not in st.session_state:
    st.session_state.api_response = None
if "selected_pdf" not in st.session_state:
    st.session_state.selected_pdf = None
if "pdfs" not in st.session_state:
    st.session_state.pdfs = []

def upload_pdf(file) -> Optional[dict]:
    """Upload PDF file to backend."""
    if file is None:
        return None
    
    try:
        files = {"file": (file.name, file.getvalue(), "application/pdf")}
        response = requests.post(f"{BACKEND_URL}/api/pdf/upload", files=files)
        if response.status_code == 200:
            return response.json()
        else:
            return {"success": False, "error": f"Upload failed with status code: {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_pdf_list():
    """Get list of processed PDFs."""
    try:
        response = requests.get(f"{BACKEND_URL}/api/pdf/list")
        return response.json() if response.status_code == 200 else []
    except Exception as e:
        st.error(f"Error fetching PDFs: {str(e)}")
        return []

def get_summary(filename: str, model: str = "gpt-4", max_length: int = 1000) -> Optional[dict]:
    """Get summary of the PDF."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/summarize",
            json={"filename": filename, "model": model, "max_length": max_length}
        )
        return response.json() if response.status_code == 200 else {"error": f"Failed to get summary: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def ask_question(filename: str, question: str, model: str = "gpt-4") -> Optional[dict]:
    """Ask a question about the PDF."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/ask",
            json={"filename": filename, "question": question, "model": model}
        )
        return response.json() if response.status_code == 200 else {"error": f"Failed to get answer: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def open_pdf_in_browser(url: str):
    """Open PDF in a new browser tab."""
    webbrowser.open_new_tab(url)

def main():
    st.title("📚 LLM PDF Assistant")
    
    # Sidebar for model selection and configuration
    with st.sidebar:
        st.header("Configuration")
        model_options = {
            "gpt-4": "OpenAI GPT-4",
            "gemini-pro": "Google Gemini Pro",
            "claude-3": "Anthropic Claude 3",
            "deepseek-chat": "DeepSeek Chat",
            "grok-1": "xAI Grok-1"
        }
        st.session_state.selected_model = st.selectbox(
            "Select LLM Model",
            options=list(model_options.keys()),
            format_func=lambda x: model_options[x]
        )

        # Display token usage and cost if available
        if st.session_state.api_response and "usage" in st.session_state.api_response:
            st.subheader("Usage Statistics")
            usage = st.session_state.api_response["usage"]
            st.write(f"Input tokens: {usage.get('input_tokens', 0)}")
            st.write(f"Output tokens: {usage.get('output_tokens', 0)}")
            st.write(f"Cost: ${usage.get('cost', 0):.4f}")

    # PDF Upload Section (moved outside tabs)
    uploaded_file = st.file_uploader("Upload a new PDF", type=['pdf'])
    if uploaded_file:
        with st.spinner("Processing PDF..."):
            result = upload_pdf(uploaded_file)
            if result:
                if result.get("success", False):
                    st.success("PDF uploaded and processed successfully!")
                    if result.get("s3_url"):
                        st.markdown(f"[View PDF in Browser]({result['s3_url']})")
                    st.session_state.pdfs = get_pdf_list()
                else:
                    st.error(f"Error: {result.get('error', 'Unknown error occurred')}")
            else:
                st.error("Failed to process the PDF. Please try again.")

    # PDF Selection Section (moved outside tabs)
    st.subheader("Select a PDF")
    if st.button("Refresh PDF List"):
        st.session_state.pdfs = get_pdf_list()
    
    # Create columns for the PDF list
    if st.session_state.pdfs:
        for pdf in st.session_state.pdfs:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                if st.button(f"📄 {pdf.get('filename', 'Unnamed')}", key=f"select_{pdf.get('filename', 'unnamed')}"):
                    st.session_state.selected_pdf = pdf.get('filename')
                    st.session_state.current_s3_url = pdf.get('s3_url')
            with col2:
                st.write(f"Pages: {pdf.get('pages', 'N/A')}")
            with col3:
                if pdf.get('s3_url'):
                    st.markdown(f"[View PDF]({pdf['s3_url']})")
    else:
        st.info("No PDFs available. Upload one to get started!")

    # Display currently selected PDF
    if st.session_state.selected_pdf:
        st.success(f"Currently selected: {st.session_state.selected_pdf}")
        if hasattr(st.session_state, 'current_s3_url'):
            st.markdown(f"[View Current PDF]({st.session_state.current_s3_url})")

    # Main content area with tabs
    tab1, tab2 = st.tabs(["📤 Process PDF", "❓ Ask Questions"])

    with tab1:
        st.header("Process Selected PDF")
        if st.session_state.selected_pdf:
            # Add Summarize button
            if st.button("Generate Summary", key="summarize_btn_tab1"):
                with st.spinner("Generating summary..."):
                    summary_result = get_summary(st.session_state.selected_pdf, st.session_state.selected_model)
                    if summary_result and "error" not in summary_result:
                        st.session_state.api_response = summary_result
                        st.success("Summary generated successfully!")
                    else:
                        st.error(f"Error generating summary: {summary_result.get('error', 'Unknown error')}")
            
            # Display summary if available
            if st.session_state.api_response and "summary" in st.session_state.api_response:
                with st.expander("Document Summary", expanded=True):
                    st.write(st.session_state.api_response["summary"])
        else:
            st.info("Please select a PDF first")

    with tab2:
        st.header("Ask Questions About Selected PDF")
        if st.session_state.selected_pdf:
            # Display summary if available
            if st.session_state.api_response and "summary" in st.session_state.api_response:
                with st.expander("Document Summary", expanded=True):
                    st.write(st.session_state.api_response["summary"])
            
            # Question input
            question = st.text_input("What would you like to know about the document?")
            if st.button("Ask"):
                if question:
                    with st.spinner("Getting answer..."):
                        answer = ask_question(
                            st.session_state.selected_pdf,
                            question,
                            st.session_state.selected_model
                        )
                        if answer and "error" not in answer:
                            st.session_state.api_response = answer
                            st.write("Answer:")
                            st.write(answer.get("answer", "No answer available"))
                        else:
                            st.error(f"Error: {answer.get('error', 'Failed to get answer')}")
        else:
            st.info("Please select a PDF first")

if __name__ == "__main__":
    main() 
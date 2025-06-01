import streamlit as st
import google.generativeai as genai
import json
import os
import uuid
from datetime import datetime
import time

# Import our custom modules
from agents import ClassifierAgent, JSONAgent, EmailAgent, PDFAgent
from memory import RedisMemory

# Configure the page
st.set_page_config(
    page_title="Document Processing",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply modern dark theme CSS
st.markdown('''
<style>
    /* Base theme */
    .main {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #e2e8f0;
    }
    
    /* Typography */
    h1, h2, h3, h4, h5, h6 {
        color: #f8fafc;
        font-family: 'Inter', sans-serif;
    }
    p, li, div {
        font-family: 'Inter', sans-serif;
    }
    
    /* Cards */
    .card {
        background: rgba(30, 41, 59, 0.7);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid rgba(100, 116, 139, 0.2);
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    /* Status badges */
    .badge {
        display: inline-flex;
        align-items: center;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
        margin-right: 8px;
    }
    .badge-blue {
        background: rgba(56, 189, 248, 0.2);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.3);
    }
    .badge-green {
        background: rgba(34, 197, 94, 0.2);
        color: #22c55e;
        border: 1px solid rgba(34, 197, 94, 0.3);
    }
    .badge-amber {
        background: rgba(251, 191, 36, 0.2);
        color: #fbbf24;
        border: 1px solid rgba(251, 191, 36, 0.3);
    }
    
    /* Upload area */
    .upload-area {
        border: 2px dashed rgba(56, 189, 248, 0.5);
        border-radius: 12px;
        padding: 40px 20px;
        text-align: center;
        background: rgba(30, 41, 59, 0.4);
        transition: all 0.3s ease;
    }
    .upload-area:hover {
        border-color: #38bdf8;
        background: rgba(30, 41, 59, 0.6);
    }
    
    /* Process steps */
    .step {
        background: rgba(30, 41, 59, 0.5);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
        border-left: 3px solid #38bdf8;
    }
    .step-header {
        display: flex;
        align-items: center;
        margin-bottom: 12px;
    }
    .step-number {
        background: #38bdf8;
        color: #0f172a;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        margin-right: 12px;
    }
    
    /* Progress bar */
    .stProgress > div > div > div {
        background-color: #38bdf8;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: rgba(30, 41, 59, 0.7);
        border-radius: 8px 8px 0 0;
        padding: 8px 16px;
        border: none;
    }
    .stTabs [aria-selected="true"] {
        background-color: rgba(56, 189, 248, 0.2);
        border-bottom: 2px solid #38bdf8;
    }
    
    /* Remove widget backgrounds */
    div.stButton > button {
        background-color: #38bdf8;
        color: #0f172a;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-weight: 500;
    }
    div.stButton > button:hover {
        background-color: #0ea5e9;
    }
    div.stFileUploader > div {
        background-color: transparent !important;
    }
    
    /* JSON viewer */
    .json-viewer {
        background-color: rgba(15, 23, 42, 0.7);
        border-radius: 8px;
        padding: 16px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.9rem;
        overflow-x: auto;
        border: 1px solid rgba(100, 116, 139, 0.2);
    }
    
    /* History items */
    .history-item {
        background: rgba(30, 41, 59, 0.5);
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
        cursor: pointer;
        transition: all 0.2s ease;
        border: 1px solid rgba(100, 116, 139, 0.1);
    }
    .history-item:hover {
        background: rgba(30, 41, 59, 0.8);
        border-color: rgba(56, 189, 248, 0.3);
    }
    .history-item.active {
        background: rgba(56, 189, 248, 0.1);
        border-left: 3px solid #38bdf8;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: rgba(15, 23, 42, 0.7);
        border-right: 1px solid rgba(100, 116, 139, 0.2);
    }
    [data-testid="stSidebarNav"] {
        padding-top: 2rem;
    }
    [data-testid="stSidebarNavItems"] {
        padding-left: 1rem;
    }
    
    /* Footer */
    footer {
        visibility: hidden;
    }
</style>

<!-- Import Google Fonts -->
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono&display=swap" rel="stylesheet">
''', unsafe_allow_html=True)

# Initialize session state
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())
if "processing_history" not in st.session_state:
    st.session_state.processing_history = []
if "selected_history_item" not in st.session_state:
    st.session_state.selected_history_item = None

# Set your Gemini API key
api_key = "******************************"  # Replace with your actual key
genai.configure(api_key=api_key)

# Load the Gemini model
model = genai.GenerativeModel(model_name="gemini-1.5-flash")

# Initialize agents
classifier_agent = ClassifierAgent(model)
json_agent = JSONAgent(model)
email_agent = EmailAgent(model)
pdf_agent = PDFAgent(model)

# Initialize Redis memory with proper error handling
try:
    memory = RedisMemory(host='localhost', port=6379, db=0)
    redis_available = True
except Exception as e:
    redis_available = False
    # Fallback to in-memory storage
    class InMemoryStorage:
        def __init__(self):
            self.storage = {}
            
        def store_document_data(self, conversation_id, source, format_type, intent, extracted_data):
            self.storage[f"doc:{conversation_id}"] = {
                "source": source,
                "format": format_type,
                "intent": intent,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "extracted_data": extracted_data
            }
            
        def get_document_data(self, conversation_id):
            return self.storage.get(f"doc:{conversation_id}")
            
        def list_all_documents(self):
            return list(self.storage.keys())
            
    memory = InMemoryStorage()

# Format JSON with syntax highlighting
def format_json(json_data):
    if isinstance(json_data, str):
        try:
            json_data = json.loads(json_data)
        except:
            return f"<pre>{json_data}</pre>"
    
    return f"<pre>{json.dumps(json_data, indent=2)}</pre>"

# Sidebar with system status
with st.sidebar:
    st.markdown("<h2>📊 System Status</h2>", unsafe_allow_html=True)
    
    # System status indicators
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"<div class='badge badge-blue'>ID: {st.session_state.conversation_id[:8]}...</div>", unsafe_allow_html=True)
    with col2:
        if redis_available:
            st.markdown("<div class='badge badge-green'>Redis Connected</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='badge badge-amber'>In-Memory Storage</div>", unsafe_allow_html=True)

# Main content with tabs
tabs = st.tabs(["📄 Upload", "📋 History", "🧠 Memory"])

# Upload Tab
with tabs[0]:
    st.markdown("<h1>📄 Document Processing System</h1>", unsafe_allow_html=True)
    
    # File upload section
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h2>Upload Document</h2>", unsafe_allow_html=True)
    
    # Upload area
    st.markdown("<div class='upload-area'>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Choose a PDF, JSON, or Email/Text file", 
                                    type=["pdf", "json", "txt"],
                                    label_visibility="collapsed")
    if not uploaded_file:
        st.markdown("<p>Drag and drop your file here or click to browse</p>", unsafe_allow_html=True)
        st.markdown("<p style='color:#94a3b8; font-size:0.9rem;'>Supported formats: PDF, JSON, TXT</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Process the uploaded file
    if uploaded_file is not None:
        # File info
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<h2>File Information</h2>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"<p><strong>Name:</strong> {uploaded_file.name}</p>", unsafe_allow_html=True)
            file_type = uploaded_file.type if hasattr(uploaded_file, 'type') else "Unknown"
            st.markdown(f"<p><strong>Type:</strong> {file_type}</p>", unsafe_allow_html=True)
        with col2:
            file_size = round(uploaded_file.size / 1024, 2) if hasattr(uploaded_file, 'size') else "Unknown"
            st.markdown(f"<p><strong>Size:</strong> {file_size} KB</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Processing pipeline
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<h2>Processing Pipeline</h2>", unsafe_allow_html=True)
        
        # Read file content
        file_content = uploaded_file.read()
        
        # Step 1: Classify document
        with st.spinner():
            st.markdown("<div class='step'>", unsafe_allow_html=True)
            st.markdown("<div class='step-header'><div class='step-number'>1</div> <strong>Document Classification</strong></div>", unsafe_allow_html=True)
            progress_bar = st.progress(0)
            for i in range(100):
                progress_bar.progress(i + 1)
                time.sleep(0.01)
            classification = classifier_agent.classify_document(file_content, uploaded_file.name)
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"<div class='badge badge-blue'>Format: {classification['format']}</div>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"<div class='badge badge-blue'>Intent: {classification['intent']}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Step 2: Process with appropriate agent
        with st.spinner():
            st.markdown("<div class='step'>", unsafe_allow_html=True)
            st.markdown("<div class='step-header'><div class='step-number'>2</div> <strong>Specialized Agent Processing</strong></div>", unsafe_allow_html=True)
            progress_bar = st.progress(0)
            for i in range(100):
                progress_bar.progress(i + 1)
                time.sleep(0.01)
            
            agent_name = "JSON Agent" if classification['format'] == "JSON" else "PDF Agent" if classification['format'] == "PDF" else "Email Agent"
            st.markdown(f"<div class='badge badge-blue'>Agent: {agent_name}</div>", unsafe_allow_html=True)
            
            if classification['format'] == "JSON":
                result = json_agent.process_json(file_content)
            elif classification['format'] == "PDF":
                result = pdf_agent.process_pdf(file_content)
            else:  # Email or Text
                result = email_agent.process_email(file_content)
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Step 3: Store in memory
        with st.spinner():
            st.markdown("<div class='step'>", unsafe_allow_html=True)
            st.markdown("<div class='step-header'><div class='step-number'>3</div> <strong>Memory Storage</strong></div>", unsafe_allow_html=True)
            progress_bar = st.progress(0)
            for i in range(100):
                progress_bar.progress(i + 1)
                time.sleep(0.005)
            
            memory.store_document_data(
                st.session_state.conversation_id,
                uploaded_file.name,
                classification['format'],
                classification['intent'],
                result
            )
            
            storage_type = "Redis Database" if redis_available else "In-Memory Storage"
            st.markdown(f"<div class='badge badge-blue'>Storage: {storage_type}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Display results
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<h2>Processing Results</h2>", unsafe_allow_html=True)
        
        # Format the result based on document type
        if classification['format'] == "JSON" and "fields" in result:
            # For RFQ or structured data
            for key, value in result.get("fields", {}).items():
                st.markdown(f"<div style='display:flex; margin-bottom:8px;'><div style='min-width:120px; font-weight:500;'>{key}:</div> <div>{value}</div></div>", unsafe_allow_html=True)
            
            if "anomalies" in result and result["anomalies"]:
                st.markdown("<h3>Anomalies</h3>", unsafe_allow_html=True)
                for anomaly in result["anomalies"]:
                    st.markdown(f"<p>• {anomaly}</p>", unsafe_allow_html=True)
        
        elif classification['format'] in ["Email", "PDF"] and "entities" in result:
            # For Email or PDF
            col1, col2 = st.columns(2)
            with col1:
                sender = result.get('sender', 'Unknown')
                st.markdown(f"<div style='display:flex; margin-bottom:8px;'><div style='min-width:120px; font-weight:500;'>Sender:</div> <div>{sender}</div></div>", unsafe_allow_html=True)
            with col2:
                urgency = result.get('urgency', 'MEDIUM')
                urgency_color = "#ef4444" if urgency == "HIGH" else "#f59e0b" if urgency == "MEDIUM" else "#10b981"
                st.markdown(f"<div style='display:flex; margin-bottom:8px;'><div style='min-width:120px; font-weight:500;'>Urgency:</div> <div style='color:{urgency_color};'>{urgency}</div></div>", unsafe_allow_html=True)
            
            st.markdown("<h3>Extracted Entities</h3>", unsafe_allow_html=True)
            
            # Check if entities contains an error message
            if isinstance(result.get("entities"), dict) and "error" in result.get("entities", {}):
                st.markdown("<div class='json-viewer'>", unsafe_allow_html=True)
                st.markdown(format_json(result), unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                for key, value in result.get("entities", {}).items():
                    st.markdown(f"<div style='display:flex; margin-bottom:8px;'><div style='min-width:120px; font-weight:500;'>{key}:</div> <div>{value}</div></div>", unsafe_allow_html=True)
        
        else:
            # Generic JSON display for any other format
            st.markdown("<div class='json-viewer'>", unsafe_allow_html=True)
            st.markdown(format_json(result), unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Add to processing history
        st.session_state.processing_history.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "file": uploaded_file.name,
            "classification": classification,
            "result": result
        })

# History tab
with tabs[1]:
    st.markdown("<h1>📋 Processing History</h1>", unsafe_allow_html=True)
    
    if not st.session_state.processing_history:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.info("No documents have been processed yet. Upload a document to get started.")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        # Two-column layout for history
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("<h2>Document List</h2>", unsafe_allow_html=True)
            
            # Display history items as clickable cards
            for idx, entry in enumerate(reversed(st.session_state.processing_history)):
                # Create a unique key for this history item
                item_key = f"{entry['timestamp']}-{entry['file']}"
                
                # Check if this item is selected
                is_selected = st.session_state.selected_history_item == item_key
                item_class = "history-item active" if is_selected else "history-item"
                
                st.markdown(f"<div class='{item_class}'>", unsafe_allow_html=True)
                st.markdown(f"<p style='color:#94a3b8; font-size:0.8rem;'>{entry['timestamp']}</p>", unsafe_allow_html=True)
                st.markdown(f"<p style='font-weight:500;'>{entry['file']}</p>", unsafe_allow_html=True)
                st.markdown(f"<div style='display:flex; gap:8px; margin-top:5px;'>", unsafe_allow_html=True)
                st.markdown(f"<span class='status status-info' style='font-size:0.7rem;'>{entry['classification']['format']}</span>", unsafe_allow_html=True)
                st.markdown(f"<span class='status status-info' style='font-size:0.7rem;'>{entry['classification']['intent']}</span>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                
                # Add a button to select this history item (hidden from UI but used for state management)
                if st.button(f"Select {idx}", key=f"select_{idx}"):
                    st.session_state.selected_history_item = item_key
                    st.experimental_rerun()
        
        with col2:
            # Display selected history item details or prompt to select an item
            if st.session_state.selected_history_item is None and len(st.session_state.processing_history) > 0:
                # Auto-select the most recent item
                st.session_state.selected_history_item = f"{st.session_state.processing_history[-1]['timestamp']}-{st.session_state.processing_history[-1]['file']}"
                st.experimental_rerun()
            
            if st.session_state.selected_history_item is not None:
                # Find the selected history item
                selected_entry = None
                for entry in st.session_state.processing_history:
                    if f"{entry['timestamp']}-{entry['file']}" == st.session_state.selected_history_item:
                        selected_entry = entry
                        break
                
                if selected_entry:
                    st.markdown("<div class='container'>", unsafe_allow_html=True)
                    st.markdown(f"<h2>{selected_entry['file']}</h2>", unsafe_allow_html=True)
                    
                    # Document details
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"<p><strong>Format:</strong> {selected_entry['classification']['format']}</p>", unsafe_allow_html=True)
                    with col2:
                        st.markdown(f"<p><strong>Intent:</strong> {selected_entry['classification']['intent']}</p>", unsafe_allow_html=True)
                    with col3:
                        st.markdown(f"<p><strong>Time:</strong> {selected_entry['timestamp']}</p>", unsafe_allow_html=True)
                    
                    st.markdown("<hr style='margin:15px 0; border:none; border-top:1px solid #2d3748;'>", unsafe_allow_html=True)
                    
                    # Processing result
                    st.markdown("<h3>Processing Result</h3>", unsafe_allow_html=True)
                    st.markdown("<div class='json-viewer'>", unsafe_allow_html=True)
                    st.markdown(format_json(selected_entry['result']), unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='container'>", unsafe_allow_html=True)
                st.info("Select a document from the list to view details")
                st.markdown("</div>", unsafe_allow_html=True)

# Memory inspection tab
with tabs[2]:
    st.markdown("<h1>🧠 Memory Inspection</h1>", unsafe_allow_html=True)
    
    # Memory data display
    st.markdown("<div class='container'>", unsafe_allow_html=True)
    st.markdown("<h2>Current Memory Data</h2>", unsafe_allow_html=True)
    
    data = memory.get_document_data(st.session_state.conversation_id)
    if data:
        st.markdown("<div class='json-viewer'>", unsafe_allow_html=True)
        st.markdown(format_json(data), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No data found for current conversation. Process a document to store data in memory.")
    st.markdown("</div>", unsafe_allow_html=True)

# Custom footer
st.markdown("<div style='margin-top:30px; text-align:center; color:#94a3b8; font-size:0.8rem;'>Multi-Agent Document Processing System v1.2.0</div>", unsafe_allow_html=True)

# Run the app
if __name__ == "__main__":
    pass  # Streamlit already runs the script

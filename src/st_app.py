import streamlit as st
import os
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ConversationBufferMemory
import chromadb
from chromadb.config import Settings
from pushing_to_vdb import MyCustomEmbeddingFunction, chroma_client, embedding_function, add_texts_by_file_to_chromadb
from prompot_router import get_dynamic_prompt
from data_preprocessing import processing_pipeline
import shutil

# --- Custom CSS for sidebar styling ---
st.markdown(
    '''
    <style>
    [data-testid="stSidebar"] {
        background: #23272f;
        padding: 2rem 1rem 2rem 1rem;
    }
    .sidebar-section-header {
        font-size: 1.3rem;
        font-weight: bold;
        color: #f9fafb;
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
    }
    .sidebar-section-box {
        background: #282c34;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    .stFileUploader {
        background: #23272f !important;
        border-radius: 8px !important;
        border: 1px solid #444 !important;
    }
    </style>
    ''',
    unsafe_allow_html=True
)
# making the 2 collections 
collection = chroma_client.get_or_create_collection(name="temp", embedding_function=embedding_function)
temp_collection = chroma_client.get_or_create_collection(name="4th_year", embedding_function=embedding_function)


# Load environment variables
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY", "")
model_name = os.getenv("MODEL_NAME", "gemini-1.5-flash")

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'selected_collection' not in st.session_state:
    st.session_state.selected_collection = "4th_year"  # default to 4th_year collection

st.title("inteliclass ChatBot")

# Collection selector
context_check = st.sidebar.radio("Context",options= ["force context","chitchat", "auto","go deep"]
                                    , index=1)


collections = ["temp", "4th_year"]
selected_collection = st.sidebar.selectbox(
    "Select Knowledge Base:",
    collections,
    index=collections.index(st.session_state.get('selected_collection', '4th_year')),
    disabled=not (context_check == "force context" or context_check == "go deep")
)


# Update session state if collection changes
if selected_collection != st.session_state.selected_collection:
    st.session_state.selected_collection = selected_collection
    st.session_state.messages = []  # Clear chat history when switching collections

# Initialize the model
if not google_api_key:
    st.error("GOOGLE_API_KEY not found in environment variables!")
    st.stop()

model = ChatGoogleGenerativeAI(
    model=model_name,
    google_api_key=google_api_key,
    temperature=0.1
)

# Initialize vectorstore and retriever for selected collection
try:
    collection = chroma_client.get_collection(name=selected_collection)
    vectorstore = Chroma(
        client=chroma_client,
        collection_name=selected_collection,
        embedding_function=embedding_function
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
except Exception as e:
    st.error(f"Error loading collection '{selected_collection}': {e}")
    st.stop()

def get_context(input_dict):
    """Get the context for the question & find the most relevant documents"""
    question = input_dict["question"]
    docs = retriever.invoke(question)
    context_parts = []
    for doc in docs:
        source = doc.metadata.get('source_file', 'Unknown source')
        context_part = f"[{source}]\n{doc.page_content}"
        context_parts.append(context_part)
    return "\n\n".join(context_parts)

def get_chat_history(input_dict):
    """Format chat history for the model"""
    chat_history = input_dict.get("chat_history", [])
    if not chat_history:
        return ""
    formatted_history = []
    for message in chat_history:
        if hasattr(message, 'content'):
            if hasattr(message, 'type') and message.type == 'human':
                formatted_history.append(f"Human: {message.content}")
            elif hasattr(message, 'type') and message.type == 'ai':
                formatted_history.append(f"Assistant: {message.content}")
            else:
                formatted_history.append(f"User: {message.content}")
    return "\n".join(formatted_history)

def get_dynamic_chain(query, context_check: str):
    """Create a dynamic chain based on the question and route"""
    prompt = get_dynamic_prompt(query, context_check)
    return (
        {
            "context": get_context,
            "question": RunnablePassthrough(),
            "chat_history": get_chat_history,
        }
        | prompt
        | model
        | StrOutputParser()
    )

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# Chat input
if prompt := st.chat_input("Ask me anything about your uploaded documents..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        # Prepare chat history for the model
        chat_history = []
        for msg in st.session_state.messages[:-1]:  # Exclude the current user message
            if msg["role"] == "user":
                chat_history.append({"type": "human", "content": msg["content"]})
            elif msg["role"] == "assistant":
                chat_history.append({"type": "ai", "content": msg["content"]})

        # Get response from the model
        with st.spinner("Thinking..."):
            try:
                chain = get_dynamic_chain(prompt,context_check)
                result = chain.invoke({
                    "question": prompt,
                    "chat_history": chat_history
                })
                
                message_placeholder.write(result)
                st.session_state.messages.append({"role": "assistant", "content": result})
                
            except Exception as e:
                error_message = f"Error generating response: {str(e)}"
                message_placeholder.markdown(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})

# Clear chat button
if st.button("Clear Chat"):
    st.session_state.messages = []
    st.rerun()

# Display collection info
with st.sidebar:
    st.header("Chat Settings")
    st.write(f"**Active Collection:** {selected_collection}")
    
    # Show collection stats
    try:
        collection_info = chroma_client.get_collection(name=selected_collection)
        count = collection_info.count()
        st.write(f"**Documents in collection:** {count}")
    except:
        st.write("**Documents in collection:** Unable to retrieve")
    
    st.divider()
    
    # File upload section
    st.header("Upload New Files")
    st.write("Upload files to the 'temp' collection for processing")
    
    if selected_collection == "temp":
        uploaded_files = st.file_uploader(
            "Choose files to upload", 
            type=["pdf","ppt","pptx"], 
            accept_multiple_files=True,
            key="chat_uploader"
        )
        
        if uploaded_files:
            st.write(f"Uploaded {len(uploaded_files)} files")
            
            if st.button("Process Files"):

                
                with st.spinner("Processing files..."):
                    results = processing_pipeline(uploaded_files)
                    
                    if results and results["cleaned_texts"]:
                        total_chunks = sum(len(texts) for texts in results["cleaned_texts"].values())
                        st.success(f"Complete! Processed into {total_chunks} chunks ready for embedding!")
                        
                        
                        try:
                            st.info("Adding to vector database...")
                            collection = chroma_client.get_or_create_collection(name="temp", embedding_function=embedding_function)
                            
                            
                            add_texts_by_file_to_chromadb(collection=collection, chunks_dir="./data/temp/chunks")
                            st.success("Successfully added to vector database!")
                            
                            # Clean up temp files
                            shutil.rmtree("./data/temp")
                            
                        except Exception as e:
                            st.error(f"Error adding to vector database: {e}")
                    else:
                        st.error("No files were successfully processed.")
    else:
        st.info("Switch to 'temp' collection to upload new files")
    st.divider()
    # Manual session cleanup button
    if st.button("End Session & Empty Temp Collection"):
        try:
            # Always target the temp collection specifically
            temp_collection = chroma_client.get_or_create_collection(name="temp", embedding_function=embedding_function)
            all_ids = temp_collection.get()['ids']
            if all_ids:
                temp_collection.delete(ids=all_ids)
                st.success("Temp collection emptied!")
            else:
                st.info("Temp collection is already empty.")
        except Exception as e:
            st.error(f"Error emptying temp collection: {e}")
        st.session_state.clear()
        st.rerun()


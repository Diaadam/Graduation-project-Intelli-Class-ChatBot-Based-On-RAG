from semantic_router import Route
from semantic_router.routers import SemanticRouter
from semantic_router.encoders import DenseEncoder
################################################################
from langchain_core.prompts import ChatPromptTemplate
###############################################################
import model_loading as model_loading
import os
from pathlib import Path
###################################################
def get_year_subject_list():
    """Get a formatted string of year and subjects from data/chunks/ files"""
    chunks_dir = Path("data/chunks")
    results = []
    
    for json_file in chunks_dir.glob("*.json"):
        filename = json_file.name.replace('.json', '')
        parts = filename.split('_')
        
        if len(parts) >= 2:
            year = parts[0]  # First part is year (2nd, 4th)
            subject = parts[1]  # Second part is subject (OOP, Computer, Security, etc.)
            results.append(f"{year} year {subject}")
    
    return " ".join(results)

# --- Define your Encoder ---
class MyEncoder(DenseEncoder):
    def __call__(self, docs):
        # Convert docs to list if it's not already
        if isinstance(docs, str):
            docs = [docs]
        
        result = model_loading.embed_texts(docs)
        if "embeddings" in result:
            return result["embeddings"]
        else:
            raise RuntimeError(result.get("error", "Unknown error in embedding"))


# --- Define your Routes (as previously discussed) ---
# 1. Route for skipping retrieved documents
skip_docs_route = Route(
    name="skip_retrieved_docs",
    utterances=[
        "skip the retrieved document", "don't use the context", "ignore the knowledge base",
        "answer without the provided information", "don't refer to the documents",
        "just answer from your own knowledge", "no need for the retrieved content",
        "disregard the external info", "don't retrieve any documents", "answer without context",
        "out of context", "out of knowledge base"
    ],
    threshold=0.95
)

# 2. Route for brief/summarization based on history
brief_summarize_route = Route(
    name="brief_summarization",
    utterances=[
        "be more brief", "make it simple", "give me a summary about it", "can you make it shorter?",
         "just the main points","briefly explain it again", "summarize based on history", "give a brief overview"
    ],
    threshold=0.95
)

# 3. Route for self-introduction
introduce_yourself_route = Route(
    name="introduce_yourself",
    utterances=[
        "who are you?", "tell me about yourself", "introduce yourself", "your name?",
        "what is your name?"
    ],
    threshold=0.95
)

get_context_route = Route(
    name="get_context_route",
    utterances=[
        "what is", "explain", "define", "describe", "how does","what is the meaning of","what is the definition of",
        "what is the purpose of", "what is the function of", "what is the importance of", "what is the significance of",
        "what is the difference between", "what is the similarity between", "what is the relationship between",
        "what is the cause of", "what is the effect of", "what is the solution to", "what is the reason for", "what is the reason for",
        "what is the consequence of", "what is the result of", "what is the solution to", "what is the reason for",
        "from the context", "from the knowledge base", "from the documents", "from the context", "from the knowledge base", "from the documents",
        "from the context", "from the knowledge base", "from the documents", "from the context", "from the knowledge base", "from the documents",
    ],
    threshold=0.7
)


# --- Conditional Prompt Generation Logic ---
routes = [skip_docs_route, brief_summarize_route, introduce_yourself_route, get_context_route]#  excluded
encoder = MyEncoder(name="prompot_encoder")
rl = SemanticRouter(encoder=encoder, routes=routes, auto_sync="local")


def get_dynamic_prompt(query: str | None, prompt_type: str) -> ChatPromptTemplate:
    """
    Generates a customized prompt based on the query and the route.
    """
    route_name = rl(query).name

    if prompt_type == "force context":
        route_name = "get_context_route"

    elif prompt_type == "chitchat":
        route_name = "skip_retrieved_docs"
        
    elif prompt_type == "auto":
        route_name = rl(query).name

    elif prompt_type == "go deep":
        route_name = "brief_summarization"


    base_instructions = """You are a helpful Q&A bot assisting students with their study material.
    You have access to the conversation history and should use it to provide contextual answers.

    Previous conversation:
    {chat_history}

    Current Question: {question}

    Instructions:
    - If the question is a follow-up to a previous question, reference the previous context.
    - If the question is unclear or too brief, ask for clarification.
    - Format your response with proper paragraphs, bullet points, or numbered lists when appropriate.
    - Use clear headings and subheadings for better readability.
    - Break down complex explanations into digestible sections.
    """

    if route_name == "brief_summarization":
        # Specific instructions for summarization/brevity
        prompt_content = f"""{base_instructions}
        Your primary goal is to provide a concise and insightful summary of the *provided document/context (such as a PDF, retrieved text, or external content)* if available; otherwise, summarize the *previous conversation or the last answer*.
        If a document or context is provided, focus your summary on that content. If not, use the conversation history.
        Even if the provided context is limited, always attempt to summarize or explain based on what is available. Do not ask the user to generate or provide more unless explicitly requested.
        If the context is insufficient, use your own knowledge to provide a helpful summary or explanation, and clearly indicate any limitations.
        If the question or content needs more explanation or is unclear, expand on the key points with deeper insights, detailed breakdowns, and real-life examples or analogies.
        Where appropriate, anticipate and address possible follow-up questions to help the user understand the topic more thoroughly.
        If the user asks for demos, provide them. Go as deep as the user's questions require, offering layered explanations if needed.
        If the user uses **it** in the question, treat it as a reference to the previous topic or the provided document.
        Provide only the essential and most insightful information, balancing depth with clarity.
        context: {{context}}
        Response Format:
        - Use bullet points for key takeaways
        - Keep each point brief and clear
        - Use bold text for important concepts
        - Structure with clear sections if needed

        Answer:"""

    elif route_name == "skip_retrieved_docs":
        # Specific instructions for skipping docs
        prompt_content = f"""{base_instructions}
        You have been instructed to answer the current question *without* using any provided context or retrieved documents.
        Rely solely on your inherent knowledge and the conversation history.
        Do NOT include any citations or references to external documents.

        Answer:"""
                # Note: 'context' will likely be an empty string or None when passing to the LLM
                # after this route is detected, so the prompt won't reference it.


    elif route_name == "introduce_yourself" or route_name == "chitchat":
        year_subject_str = get_year_subject_list()
        
        return ChatPromptTemplate.from_template(
            """You are a helpful Q&A bot. A user is asking you to introduce yourself.
            Here is the list of the year and subject that you currently has access to: {0}
            
            Instructions:
            - Respond directly with a brief introduction.
            - Do not answer any other question the user might have asked in the same query.
            - Format your response in a  welcoming manner.
            
            Answer example: Hello! I am a helpful AI assistant designed to assist students with their study materials and answer questions. I have access to materials covering: {0}. How can I help you today?
            """.format(year_subject_str)
        )
    elif route_name == "get_context_route":
        prompt_content = f"""{base_instructions}
        Answer the question comprehensively based on the following context and conversation history.
        Always include citations in the format [filename] for each piece of information you reference.
        If the context does not contain enough information to fully answer the question, state that you cannot fully answer from the provided materials.

        Response Format:
        - Start with a clear, concise answer
        - Use bullet points or numbered lists for multiple concepts
        - Separate different topics with line breaks
        - Include relevant examples when helpful
        - End with a brief summary if the topic is complex

        Context: {{context}}

        Answer:"""

    else: # Default RAG behavior if no specific route is matched or for general queries
        prompt_content = base_instructions


    return ChatPromptTemplate.from_template(prompt_content)


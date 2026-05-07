# import chromadb
from chromadb.config import Settings
import chromadb
from chromadb.utils.embedding_functions import EmbeddingFunction
import json
import os
import uuid
from model_loading import embed_texts

class MyCustomEmbeddingFunction(EmbeddingFunction):
    def __init__(self):
        """Initialize the embedding function using the loaded model from model_loading.py"""
        # The model is already loaded in model_loading.py when the module is imported
        pass
        
    def get_embeddings(self, texts):
        """Get embeddings using the loaded model"""
        if not texts:
            return []
        
        # Use the embed_texts function from model_loading.py
        result = embed_texts(texts)
        
        if "error" in result:
            print(f"Embedding error: {result['error']}")
            return []
        
        if "embeddings" in result:
            return result["embeddings"]
        
        return []
    
    def __call__(self, input_texts):
        """Call the embedding function"""
        # Add 'passage:' prefix to each text unless already present
        prefixed_texts = [
            f"passage: {text}" if not text.startswith("passage:") else text
            for text in input_texts
        ]
        return self.get_embeddings(prefixed_texts)
        
    def embed_query(self, query):
        """Embed a single query"""
        if not (query.startswith("query:") or query.startswith("passage:")):
            query = f"query: {query}"
        embeddings = self.get_embeddings([query])
        return embeddings[0] if embeddings else []

def add_texts_by_file_to_chromadb(collection, chunks_dir="./data/chunks", year_filter=None):
    """
    Load chunk files from the chunks directory and add them to ChromaDB.
    
    Args:
        collection: ChromaDB collection to add documents to
        chunks_dir (str): Directory containing chunk JSON files
        year_filter (str, optional): Filter files by year (e.g., "2nd", "4th"). 
                                   If None, processes all files.
    """
    total_texts_added = 0
    files_processed = 0
    
    if not os.path.exists(chunks_dir):
        print(f"Chunks directory {chunks_dir} does not exist.")
        return
    
    for filename in os.listdir(chunks_dir):
        if filename.endswith('.json'):
            # Extract year from filename (e.g., "2nd_OOP_lec_7-generics.json" -> "2nd")
            file_year = filename.split('_')[0] if '_' in filename else None
            
            # Apply year filter if specified
            if year_filter is not None and file_year != year_filter:
                continue
            
            file_path = os.path.join(chunks_dir, filename)
            print(f"Processing chunks from {filename}...")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    chunks_data = json.load(f)
                
                # Extract texts and metadata from chunks
                texts = []
                ids = []
                metadatas = []
                
                for chunk in chunks_data:
                    if isinstance(chunk, dict) and 'text' in chunk and 'id' in chunk:
                        texts.append(chunk['text'])
                        ids.append(chunk['id'])
                        metadatas.append({
                            "source_file": chunk.get('source_file', filename.replace('.json', '')),
                            "chunk_index": chunk.get('chunk_index', 0),
                            "year": file_year  # Add year to metadata
                        })
                
                if texts:
                    collection.add(documents=texts, ids=ids, metadatas=metadatas)
                    total_texts_added += len(texts)
                    files_processed += 1
                    print(f"  Added {len(texts)} chunks from {filename}")
                else:
                    print(f"  No valid chunks found in {filename}")
                    
            except Exception as e:
                print(f"  Error processing {filename}: {e}")
                continue
    
    filter_info = f" (filtered by year: {year_filter})" if year_filter else ""
    print(f"Total: Added {total_texts_added} texts to ChromaDB from {files_processed} files{filter_info}")

def chroma_retrieve(collection, query, content_key="content", top_k=5):
    results = collection.query(query_texts=[query], n_results=top_k)
    docs = results.get('documents', [[]])[0]
    metadatas = results.get('metadatas', [[]])[0]
    return [
        {
            content_key: doc,
            "metadata": meta
        } for doc, meta in zip(docs, metadatas)
    ]



# Define embedding function using the loaded model
embedding_function = MyCustomEmbeddingFunction()
chroma_client = chromadb.Client(Settings(is_persistent= True,persist_directory=r"chroma_db"))

# collection = chroma_client.get_or_create_collection(name="test",embedding_function=embedding_function)


# Example usage:
# add_texts_by_file_to_chromadb(collection=collection, chunks_dir="./data/chunks")  # Process all files
# add_texts_by_file_to_chromadb(collection=collection, chunks_dir="./data/chunks", year_filter="2nd")  # Process only 2nd year files
# add_texts_by_file_to_chromadb(collection=collection, chunks_dir="./data/chunks", year_filter="4th")  # Process only 4th year files

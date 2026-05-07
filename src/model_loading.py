import torch
from transformers import AutoTokenizer, AutoModel
import os
from dotenv import load_dotenv

load_dotenv()
# loading the model 

MODEL_PATH = os.getenv("MODEL_PATH", "./model/e5-base-v2") #model\e5-base-v2
global_tokenizer = None
global_model = None

def load_model():
    global global_tokenizer, global_model
    try:
        print(f"Loading model from {MODEL_PATH} using transformers...")
        global_tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
        global_model = AutoModel.from_pretrained(MODEL_PATH)
        global_model.eval()
        print("Model loaded successfully.")
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to load model: {e}")
        global_tokenizer = None
        global_model = None


def embed_texts(texts):
    """
    E5 models are specifically designed for sentence embeddings and use mean pooling instead of [CLS] token pooling.
    The [CLS] token in E5 models doesn't contain the sentence-level semantic information like it does in standard BERT.
    """
    if global_model is None or global_tokenizer is None:
        return {"error": "Model not ready. Please try again later."}
    
    if not isinstance(texts, list) or not all(isinstance(t, str) for t in texts):
        return {"error": "Invalid input. 'texts' must be a list of strings."}
    
    # # Add prefix for E5 model if not already present
    # prefixed_texts = [f"query: {text}" if not (text.startswith("query:") or text.startswith("passage:")) else text for text in texts]
    
    try:
        with torch.no_grad():
            inputs = global_tokenizer(texts, padding=True, truncation=True, return_tensors="pt")
            outputs = global_model(**inputs)
            
            # For E5 models, use mean pooling over all tokens (excluding special tokens)
            attention_mask = inputs['attention_mask']
            token_embeddings = outputs.last_hidden_state
            
            # Create mask for non-special tokens
            input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
            
            # Sum embeddings and divide by number of tokens (mean pooling)
            sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
            sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
            embeddings = sum_embeddings / sum_mask
            
            # Convert to numpy and then to list
            embeddings = embeddings.cpu().numpy()
            embeddings = [e.tolist() for e in embeddings]
            
        return {"embeddings": embeddings}
    except Exception as e:
        return {"error": f"Error during embedding generation: {e}"}

# Load the model when module is imported
# or use load_model()
# model_loading.load_model()
# # embed_texts = model_loading.embed_texts(["please, embedd these"])
load_model()



# import model_loading

# Example usage
# texts = ["Hello world", "How are you?"]
# result = model_loading.embed_texts(texts)

# if "error" in result:
#     print(f"Error: {result['error']}")
# else:
#     embeddings = result['embeddings']
#     print(f"Generated {len(embeddings)} embeddings")
#     print(f"Each embedding has {len(embeddings[0])} dimensions")
#     print(result)
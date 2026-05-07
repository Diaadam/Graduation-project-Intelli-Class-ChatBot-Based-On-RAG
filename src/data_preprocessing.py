#example usage

# from data_preprocessing import unstructured_API_processing
# # Using default paths
# unstructured_API_processing("4nd", "embedded")

import os
import json
import dotenv
import uuid
from unstructured.chunking.title import chunk_by_title
from unstructured.staging.base import dict_to_elements
from unstructured_client import UnstructuredClient
from unstructured_client.models import operations, shared
#os
from unstructured.partition.auto import partition
from unstructured.cleaners.core import replace_unicode_quotes, bytes_string_to_string
from unstructured.cleaners.core import clean_ordered_bullets, clean_bullets
from unstructured.documents.elements import Text
import shutil
from unstructured.partition.pptx import partition_pptx



dotenv.load_dotenv()
api_key_auth = dotenv.dotenv_values().get('UNSTRUCT_API_KEY')
server_url = dotenv.dotenv_values().get('UNSTRUCT_API_URL')


client = UnstructuredClient(
    api_key_auth=api_key_auth,
    server_url=server_url,
)

############################(preprocessing)#############################

def unstructured_API_pdf_prepare(file_path, strategy=shared.Strategy.AUTO, document_type="slides_as_pdf"):
    filename = os.path.basename(file_path)
    if not filename.lower().endswith(".pdf"):
        print(f"File {file_path} is not a PDF.")
        elements1 = partition(filename=filename) # know the type using libmagic
        return None

    print(f"Processing file {file_path}")
    # Parameters
    chunking_strategy = "by_page" if document_type == "slides_as_pdf" else "similarity"
    combine_text_under_n_chars = 1000
    max_characters = 2000 if document_type == "slides_as_pdf" else 1500
    multipage_sections = False if document_type == "slides_as_pdf" else True

    # Check if API credentials are available
    if not api_key_auth or not server_url:
        print("API credentials not found. Using local partition.")
        try:
            res = partition(filename=file_path, content_type="application/pdf")
            element_dicts = [el.to_dict() for el in res]
            return json.dumps(element_dicts, indent=2)
        except Exception as e:
            print(f"Error processing {file_path} using local partition: {e}")
            return None

    try:
        with open(file_path, "rb") as f:
            files = shared.Files(content=f.read(), file_name=file_path)

        req = operations.PartitionRequest(
            partition_parameters=shared.PartitionParameters(
                files=files,
                content_type="pdf",
                strategy=strategy,
                chunking_strategy=chunking_strategy,
                combine_text_under_n_chars=combine_text_under_n_chars,
                max_characters=max_characters,
                multipage_sections=multipage_sections,
                extract_image_block_types=["image", "Table"],
                
            )
        )

        res = client.general.partition(request=req)
        element_dicts = [element for element in res.elements]
        return json.dumps(element_dicts, indent=2)

    except Exception as e:
        print(f"Error processing {file_path} using API: {e}")
        print(f"Processing {file_path} using local partition")
        try:
            res = partition(filename=file_path, content_type="application/pdf")
            element_dicts = [el.to_dict() for el in res]
            return json.dumps(element_dicts, indent=2)
        except Exception as local_error:
            print(f"Error processing {file_path} using local partition: {local_error}")
            return None


        


def unstructured_API_processing(year:str, subject:str, in_dir=None, out_dir=None,document_type="slides_as_pdf"):
    """Preprocess PDF files using Unstructured API and save results as JSON files.
        Take the unstructured_pdf_API_prepare function and apply it to all PDF files in the input directory.
        The results are saved in the output directory with the same structure as the input directory.
    """
    # Set default paths if not provided
    if in_dir is None:
        in_dir = os.path.join("data","raw", subject)
    if out_dir is None:
        out_dir = os.path.join("data", "json_files")
    
    element_dicts_prep = {}
    os.makedirs(out_dir, exist_ok=True)  # create dir if not already exist

    # Check if input directory exists
    if not os.path.exists(in_dir):
        print(f"Input directory {in_dir} does not exist.")
        return element_dicts_prep

    for dirpath, _, filenames in os.walk(in_dir):
        dir_name = os.path.basename(dirpath)
        print(f"Processing directory {dir_name}")

        for filename in filenames:
            if not filename.lower().endswith('.pdf'):
                continue  # Skip non-PDF files
                
            file_path = os.path.join(dirpath, filename)
            json_elements = unstructured_API_pdf_prepare(file_path, document_type=document_type)

            if json_elements:
                clean_name = filename.replace(" ", "_").lower().replace(".pdf", ".json")
                element_dicts_prep[clean_name] = json_elements
                output_name = f"{year}_{subject}_{clean_name}"
                output_file = os.path.join(out_dir, output_name)
                with open(output_file, "w", encoding="utf-8") as json_file:
                    json_file.write(json_elements)
                print(f"The output is in {output_file}")

    return element_dicts_prep



###########################(preprocessing pptx)###########################

def convert_to_pptx(file_path):
    """Converts a .ppt file to .pptx format."""
    try:
        new_file_path = file_path.replace(".ppt", ".pptx")
        shutil.copy(file_path, new_file_path)  # Copy the file and rename it
        print(f"Converted {file_path} to {new_file_path}")
        return new_file_path
    except Exception as e:
        print(f"Error converting {file_path} to .pptx: {e}")
        return None

def processing_pptx(year, subject, in_dir=None, out_dir=None):
    """
    Process PowerPoint files and convert them to JSON format with year and subject naming.
    
    Args:
        year (str): Year identifier (e.g., "4nd", "3rd")
        subject (str): Subject name (e.g., "embedded", "mathematics")
        in_dir (str, optional): Input directory containing PowerPoint files
        out_dir (str, optional): Output directory for JSON files
    
    Returns:
        dict: Dictionary of processed PowerPoint files
    """
    # Set default paths if not provided
    if in_dir is None:
        in_dir = os.path.join("data", "raw", subject)
    if out_dir is None:
        out_dir = os.path.join("data", "json_files")
    
    element_dicts_prep = {}
    os.makedirs(out_dir, exist_ok=True)

    # Check if input directory exists
    if not os.path.exists(in_dir):
        print(f"Input directory {in_dir} does not exist.")
        return element_dicts_prep

    for dirpath, dirnames, filenames in os.walk(in_dir):
        dir_name = os.path.basename(dirpath)
        print(f"Processing directory {dir_name}")
        
        for filename in filenames:
            # Skip temporary PowerPoint files
            if filename.startswith('~$'):
                print(f"Skipping temporary file: {filename}")
                continue

            if filename.endswith(".ppt") or filename.endswith(".pptx"):
                file_path = os.path.join(dirpath, filename)
                
                # Check if it's actually a PowerPoint file (simple extension check)
                if not (filename.lower().endswith('.ppt') or filename.lower().endswith('.pptx')):
                    print(f"File {file_path} is not a PowerPoint file.")
                    continue

                # Convert .ppt to .pptx if necessary
                if filename.endswith(".ppt"):
                    file_path = convert_to_pptx(file_path)
                    if not file_path:  # Skip if conversion failed
                        continue

                print(f"Processing file {file_path}")

                try:
                    # Process the PowerPoint file
                    elements = partition_pptx(filename=file_path, include_slide_notes=True)
                    
                    element_dicts = [el.to_dict() for el in elements]
                    json_elements = json.dumps(element_dicts, indent=2)
                    
                    # Clean filename for dictionary key (same as PDF naming convention)
                    clean_filename = filename.replace(" ", "_").lower().replace(".pptx", "").replace(".ppt", "")
                    element_dicts_prep[clean_filename] = json_elements

                    # Create output filename with year and subject (same as PDF naming)
                    output_filename = f"{year}_{subject}_{clean_filename}.json"
                    saved_loc = os.path.join(out_dir, output_filename)
                    
                    with open(saved_loc, "w", encoding="utf-8") as json_file:
                        json_file.write(json_elements)
                    print(f"Saved: {saved_loc}")
                    
                except PermissionError as e:
                    print(f"Cannot access file {filename}: {e}")
                except Exception as e:
                    print(f"Error processing {filename}: {e}")
                    
    return element_dicts_prep



#################################(chunking)#########################################



def loading_files_to_chunk(dir="./data/json_files", year=None, subject=None):
    """
    Load JSON files from the specified directory, optionally filtered by year and subject.
    
    Args:
        dir (str): Directory path to search for JSON files
        year (str, optional): Filter files by year (e.g., "4th", "3rd")
        subject (str, optional): Filter files by subject (e.g., "embedded", "mathematics")
    
    Returns:
        dict: Dictionary of loaded JSON files with filename as key
    """
    loaded_files = {}
    
    if not os.path.exists(dir):
        print(f"Directory {dir} does not exist.")
        return loaded_files
    
    for dirpath, dirnames, filenames in os.walk(dir):
        for filename in filenames:
            if not filename.endswith(".json"):
                continue
                
            # Filter by year if specified
            if year and year not in filename:
                continue
                
            # Filter by subject if specified
            if subject and subject not in filename:
                continue
                
            file_path = os.path.join(dirpath, filename)
            print(f"Loading {file_path}")
            
            try:
                with open(file_path, "r", encoding="utf-8") as json_file:
                    loaded_json = json.load(json_file)
                    variable_name = filename.replace(".json", "")
                    loaded_files[variable_name] = loaded_json
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
                continue
    
    print(f"Loaded {len(loaded_files)} files from {dir}")
    if year:
        print(f"Filtered by year: {year}")
    if subject:
        print(f"Filtered by subject: {subject}")
        
    return loaded_files

def chunk_files_with_key(files: dict) -> dict:
    file_chunks = {}
    for file_name, file_content in files.items():
        elements = dict_to_elements(file_content)
        # Smaller, more focused chunks for better retrieval
        chunked_elements = chunk_by_title(elements, combine_text_under_n_chars=300, max_characters=800)
        file_chunks[file_name] = chunked_elements
    print(f"Chunked {len(file_chunks)} files into {sum(len(chunks) for chunks in file_chunks.values())} chunks.")
    return file_chunks

def extract_chunk_texts(file_chunks: dict) -> dict:
    file_texts = {}
    for file_name, chunks in file_chunks.items():
        texts = []
        for chunk in chunks:
            text = getattr(chunk, 'text', None)
            if text is None:
                if isinstance(chunk, dict) and 'text' in chunk:
                    text = chunk['text']
                else:
                    text = str(chunk)
            texts.append(text)
        file_texts[file_name] = texts
    print(f"Extracted {sum(len(texts) for texts in file_texts.values())} texts from chunks.")
    return file_texts

##cleaning extract_chunk_texts() texts

def clean_chunk(file_texts: dict) -> dict:
    """
    Clean the extracted text chunks using unstructured cleaners.
    
    Args:
        file_texts (dict): Dictionary with filename as key and list of text chunks as value
    
    Returns:
        dict: Dictionary with cleaned text chunks
    """
    cleaned_file_texts = {}
    
    for file_name, texts in file_texts.items():
        cleaned_texts = []
        bytes_warning_shown = False  # Track if we've shown the bytes warning for this file
        
        for text in texts:
            if not isinstance(text, str):
                text = str(text)
            
            # Create a Text element for cleaning
            text_element = Text(text)
            
            # Apply various cleaners with error handling
            cleaned_text = text_element.text
            
            # Replace unicode quotes with standard quotes
            try:
                cleaned_text = replace_unicode_quotes(cleaned_text)
            except Exception as e:
                if not bytes_warning_shown:
                    print(f"Warning: Unicode quote replacement issues in {file_name}")
                    bytes_warning_shown = True
            
            # Convert bytes strings to regular strings (with error handling)
            try:
                cleaned_text = bytes_string_to_string(cleaned_text)
            except ValueError:
                # Silently skip bytes conversion - this is expected for Unicode text
                pass
            except Exception as e:
                if not bytes_warning_shown:
                    print(f"Warning: Text encoding issues in {file_name}")
                    bytes_warning_shown = True
            
            # Clean bullets and ordered lists
            try:
                cleaned_text = clean_bullets(cleaned_text)
                cleaned_text = clean_ordered_bullets(cleaned_text)
            except Exception as e:
                if not bytes_warning_shown:
                    print(f"Warning: Bullet cleaning issues in {file_name}")
                    bytes_warning_shown = True
            
            # Additional cleaning steps
            # Remove excessive whitespace
            cleaned_text = ' '.join(cleaned_text.split())
            
            # Remove empty lines
            cleaned_text = '\n'.join(line for line in cleaned_text.split('\n') if line.strip())
            
            # Skip empty texts and very short chunks (likely noise)
            if cleaned_text.strip() and len(cleaned_text.strip()) > 50:
                cleaned_texts.append(cleaned_text)
        
        cleaned_file_texts[file_name] = cleaned_texts
    
    print(f"Cleaned {sum(len(texts) for texts in cleaned_file_texts.values())} text chunks from {len(cleaned_file_texts)} files.")
    return cleaned_file_texts

def save_cleaned_chunks(cleaned_file_texts: dict, output_dir: str = "./data/chunks") -> dict:
    """
    Save cleaned text chunks as JSON files with UUIDs for ChromaDB storage.
    
    Args:
        cleaned_file_texts (dict): Dictionary with filename as key and list of cleaned text chunks as value
        output_dir (str): Directory to save the JSON files
    
    Returns:
        dict: Dictionary mapping file names to their saved file paths
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    saved_files = {}
    
    for file_name, text_chunks in cleaned_file_texts.items():
        # Create list of chunks with UUIDs
        chunks_with_ids = []
        
        for i, text in enumerate(text_chunks):
            chunk_id = str(uuid.uuid4())
            chunks_with_ids.append({
                "id": chunk_id,
                "text": text,
                "chunk_index": i,
                "source_file": file_name
            })
        
        # Create output filename (same as the key)
        output_filename = f"{file_name}.json"
        output_path = os.path.join(output_dir, output_filename)
        
        # Save to JSON file
        try:
            with open(output_path, "w", encoding="utf-8") as json_file:
                json.dump(chunks_with_ids, json_file, indent=2, ensure_ascii=False)
            
            saved_files[file_name] = output_path
            print(f"Saved {len(chunks_with_ids)} chunks to {output_path}")
            
        except Exception as e:
            print(f"Error saving {output_path}: {e}")
            continue
    
    print(f"Successfully saved {len(saved_files)} files to {output_dir}")
    return saved_files

# function that take the raw pdf data process it  and use all the functions to make it ready for embedding
def ready_for_embedding(year=None, subject=None, in_dir="./data/json_files", out_dir="./data/chunks"):
    """
    Take the raw data and use all the functions to make it ready for embedding
    
    Args:
        year (str, optional): Filter files by year (e.g., "4th", "3rd")
        subject (str, optional): Filter files by subject (e.g., "embedded", "mathematics")
        in_dir (str): Input directory containing JSON files
        out_dir (str): Output directory for cleaned chunks
    
    Returns:
        dict: Dictionary with cleaned text chunks
    """
    print(f"Processing files for year: {year}, subject: {subject}")
    
    # Load files with filtering
    loaded_files = loading_files_to_chunk(dir=in_dir, year=year, subject=subject)
    
    if not loaded_files:
        print("No files found matching the criteria.")
        return {}
    
    # Process the files through the pipeline
    file_chunks = chunk_files_with_key(loaded_files)
    extracted_texts = extract_chunk_texts(file_chunks)
    cleaned_texts = clean_chunk(extracted_texts)
    saved_files = save_cleaned_chunks(cleaned_texts, out_dir)
    
    print(f"Pipeline complete! Processed {len(cleaned_texts)} files.")
    return cleaned_texts





def upload_files_to_temp(uploaded_files, data_dir="./data/temp/user_files"):
    """
    Save uploaded files to the temp data folder.
    
    Args:
        uploaded_files: List of Streamlit UploadedFile objects
        year (str): Year identifier for folder structure
        subject (str): Subject name for folder structure
        data_dir (str): Base data directory
    
    Returns:
        list: List of paths to saved files
    """
    
    saved_files = []  # list of paths to saved files
    
    # Create directory structure: data/temp/subject/
    temp_dir = os.path.join(data_dir)
    os.makedirs(temp_dir, exist_ok=True)
    
    for uploaded_file in uploaded_files:
        if uploaded_file is not None:
            # Get file info
            filename = uploaded_file.name
            
            # Clean filename for saving
            # clean_filename = filename.replace(" ", "_").replace("(", "").replace(")", "").replace("-", "_")
            
            # Save file path
            saved_file_path = os.path.join(temp_dir, filename)
            
            try:
                # Save the uploaded file
                with open(saved_file_path, "wb") as f:
                    f.write(uploaded_file.getvalue())
                
                saved_files.append(saved_file_path)
                print(f"Saved uploaded file to: {saved_file_path}")
                
            except Exception as e:
                print(f"Error saving uploaded file {filename}: {e}")
    
    print(f"Successfully saved {len(saved_files)} files to {temp_dir}")
    return saved_files


def processing_pipeline(uploaded_files, year="uploaded", subject="user_files", raw_dir="./data/temp/user_files", json_dir="./data/temp/json_files", chunks_dir="./data/temp/chunks"):
    """
    Complete processing pipeline for uploaded files.
    
    Args:
        uploaded_files: List of Streamlit UploadedFile objects
        year (str): Year identifier for naming
        subject (str): Subject name for naming
        data_dir (str): Base data directory
    
    Returns:
        dict: Dictionary containing all processed results
    """
    
    # Initialize result dictionaries
    all_pdf_results = {}
    all_pptx_results = {}
    all_cleaned_texts = {}
    
    # First upload files
    print(f"Uploading files for {year} {subject}...")
    saved_files = upload_files_to_temp(uploaded_files, data_dir=raw_dir)
    
    if not saved_files:
        print("No files were uploaded successfully.")
        return {}
    
    # Process PDFs
    print(f"Processing {year} {subject} PDFs...")
    try:
        pdf_result = unstructured_API_processing(year, subject, 
                                                in_dir=raw_dir, 
                                                out_dir=json_dir)
        if pdf_result:
            all_pdf_results.update(pdf_result)
            print(f"{subject}: {len(pdf_result)} PDF files processed")
        else:
            print(f"{subject}: No PDF files processed")
    except Exception as e:
        print(f"{subject}: PDF Error - {e}")

    # Process PowerPoint files
    print(f"Processing {year} {subject} PowerPoint files...")
    try:
        pptx_result = processing_pptx(year, subject, 
                                     in_dir=raw_dir, 
                                     out_dir=json_dir)
        if pptx_result:
            all_pptx_results.update(pptx_result)
            print(f"{subject}: {len(pptx_result)} PowerPoint files processed")
        else:
            print(f"{subject}: No PowerPoint files processed")
    except Exception as e:
        print(f"{subject}: PowerPoint Error - {e}")

    # Prepare for embedding
    print(f"\nPreparing for embedding {year} {subject}...")
    try:
        cleaned_texts = ready_for_embedding(year=year, subject=subject, 
                                          in_dir=json_dir, 
                                          out_dir=chunks_dir)
        if cleaned_texts:
            all_cleaned_texts.update(cleaned_texts)
            print(f"{subject}: {len(cleaned_texts)} files processed for embedding")
        else:
            print(f"{subject}: No files processed for embedding")
    except Exception as e:
        print(f"{subject}: Embedding Error - {e}")
    
    #deleting the raw files after processing the data
    if all_cleaned_texts and (all_pdf_results or all_pptx_results):
        try:
            shutil.rmtree(raw_dir)
            print(f"Successfully deleted raw files directory: {raw_dir}")
        except Exception as e:
            print(f"Error deleting raw files directory: {e}")

    return {
        "pdf_results": all_pdf_results,
        "pptx_results": all_pptx_results,
        "cleaned_texts": all_cleaned_texts
    }


    
     


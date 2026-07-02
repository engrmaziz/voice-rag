import os
import pickle
import tempfile
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LangchainDocument
from langchain_community.retrievers import BM25Retriever
from langchain_pinecone import PineconeVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader

def process_documents(queryset):
    all_chunks = []
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    
    for document in queryset:
        file_name = document.file.name.lower()
        
        # 1. Handle PDF Files (Using Tempfile Buffer for FUSE compatibility)
        if file_name.endswith('.pdf'):
            tmp_file_path = None
            try:
                # Create a temporary local file on the container's fast ephemeral disk
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    # Safely read the bytes from the mounted bucket and write locally
                    tmp_file.write(document.file.read())
                    tmp_file_path = tmp_file.name

                # Pass the local temp path to LangChain
                loader = PyPDFLoader(tmp_file_path)
                pdf_docs = loader.load()
                
                # Split the PDF pages into smaller chunks
                split_docs = text_splitter.split_documents(pdf_docs)
                
                # Append to our master list with standard metadata
                for doc in split_docs:
                    doc.metadata["title"] = document.title
                    doc.metadata["document_id"] = document.id
                    all_chunks.append(doc)
                    
            except Exception as e:
                print(f"Error reading PDF file for document {document.id}: {e}")
                continue
            finally:
                # Critical: Always clean up the temp file to prevent memory leaks
                if tmp_file_path and os.path.exists(tmp_file_path):
                    os.remove(tmp_file_path)

        # 2. Handle Text, Markdown, CSV, etc.
        else:
            content = None
            try:
                # Read bytes directly from the Django storage object
                raw_bytes = document.file.read()
                try:
                    # Attempt standard UTF-8 decoding
                    content = raw_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    # Fallback to latin-1 if it contains unexpected characters
                    content = raw_bytes.decode('latin-1')
            except Exception as e:
                print(f"Error reading text file for document {document.id}: {e}")
                continue
                
            if content:
                chunks = text_splitter.split_text(content)
                for chunk in chunks:
                    all_chunks.append(LangchainDocument(
                        page_content=chunk,
                        metadata={"title": document.title, "document_id": document.id}
                    ))
        
    if not all_chunks:
        print("No chunks to process.")
        return

    # 3. Initialize HuggingFaceEmbeddings and upsert into Pinecone
    # Using the HF Hub identifier prevents Git repository size limits
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    # INDENTATION FIXED HERE
    index_name = os.environ.get("PINECONE_INDEX_NAME", "voicerag-index").strip()    
    
    PineconeVectorStore.from_documents(
        all_chunks,
        embedding=embeddings,
        index_name=index_name
    )
    
    # 4. Build BM25Retriever and save to a local pickle file
    bm25_retriever = BM25Retriever.from_documents(all_chunks)
    with open('bm25_corpus.pkl', 'wb') as f:
        pickle.dump(bm25_retriever, f)
        
    # Mark all documents in the queryset as ingested
    for document in queryset:
        document.ingested = True
        document.save()
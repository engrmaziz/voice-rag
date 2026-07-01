import os
import pickle
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
        file_path = document.file.path
        
        # 1. Handle PDF Files
        if file_path.lower().endswith('.pdf'):
            try:
                loader = PyPDFLoader(file_path)
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

        # 2. Handle Text, Markdown, CSV, etc.
        else:
            content = None
            try:
                # Attempt standard UTF-8 reading
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                try:
                    # Fallback to latin-1 if it contains weird characters
                    with open(file_path, 'r', encoding='latin-1') as f:
                        content = f.read()
                except Exception as e:
                    print(f"Fallback reading failed for document {document.id}: {e}")
                    continue
            except Exception as e:
                print(f"Error reading file for document {document.id}: {e}")
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
    # Replace the existing embeddings initialization line with this:
embeddings = HuggingFaceEmbeddings(
    model_name="./all-MiniLM-L6-v2", 
    encode_kwargs={'normalize_embeddings': True}
)
index_name = os.environ.get("PINECONE_INDEX_NAME", "default-index")
    
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
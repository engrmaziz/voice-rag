import os
import pickle
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LangchainDocument
from langchain_community.retrievers import BM25Retriever
from langchain_pinecone import PineconeVectorStore
from langchain_huggingface import HuggingFaceEmbeddings

def process_documents(queryset):
    all_chunks = []
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    
    for document in queryset:
        # Read the file content
        try:
            document.file.open('r')
            content = document.file.read()
            
            # Ensure content is string
            if isinstance(content, bytes):
                content = content.decode('utf-8')
                
        except Exception as e:
            print(f"Error reading file for document {document.id}: {e}")
            continue
        finally:
            document.file.close()
            
        # Split the text into chunks
        chunks = text_splitter.split_text(content)
        
        # Convert to LangChain documents
        for chunk in chunks:
            all_chunks.append(LangchainDocument(
                page_content=chunk,
                metadata={"title": document.title, "document_id": document.id}
            ))
            
    if not all_chunks:
        print("No chunks to process.")
        return

    # 1. Initialize HuggingFaceEmbeddings and upsert into Pinecone
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    index_name = os.environ.get("PINECONE_INDEX_NAME", "default-index")
    
    PineconeVectorStore.from_documents(
        all_chunks,
        embedding=embeddings,
        index_name=index_name
    )
    
    # 2. Build BM25Retriever and save to a local pickle file
    bm25_retriever = BM25Retriever.from_documents(all_chunks)
    with open('bm25_corpus.pkl', 'wb') as f:
        pickle.dump(bm25_retriever, f)
        
    # Mark all documents in the queryset as ingested
    for document in queryset:
        document.ingested = True
        document.save()

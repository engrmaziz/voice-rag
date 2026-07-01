
import os
import pickle
from pydantic import BaseModel, Field
from sentence_transformers import CrossEncoder
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_pinecone import PineconeVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from graph.state import GraphState

def rewrite_query(state: GraphState) -> GraphState:
    """
    Rewrites the question into a standalone question based on recent chat history.
    """
    question = state["question"]
    chat_history = state.get("chat_history", [])
    
    # Take the last 4 messages
    recent_history = chat_history[-4:] if len(chat_history) > 0 else []
    
    # Format history for the prompt
    history_str = "\n".join([str(msg) for msg in recent_history])
    
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    
    prompt = PromptTemplate(
        template="""You are an expert conversational assistant. 
Given the following conversation history and the user's current question, rewrite the current question into a fully standalone question that does not depend on prior turns.
Do not answer the question, just rewrite it. If the question is already standalone, simply return it as is.

Conversation History:
{history}

Current Question: {question}

Standalone Question:""",
        input_variables=["history", "question"],
    )
    
    chain = prompt | llm
    response = chain.invoke({"history": history_str, "question": question})
    
    rewritten_question = response.content.strip()
    
    # Return the updated state
    return {"question": rewritten_question}

def hybrid_retrieve(state: GraphState) -> GraphState:
    """
    Retrieves documents using an EnsembleRetriever (BM25 + Pinecone).
    """
    question = state["question"]
    
    # Load BM25 Retriever
    with open('bm25_corpus.pkl', 'rb') as f:
        bm25_retriever = pickle.load(f)
    bm25_retriever.k = 10
    
    # Setup Pinecone VectorStore Retriever
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    index_name = os.environ.get("PINECONE_INDEX_NAME", "default-index")
    vectorstore = PineconeVectorStore(index_name=index_name, embedding=embeddings)
    pinecone_retriever = vectorstore.as_retriever(search_kwargs={"k": 10})
    
    # Create Ensemble Retriever
    ensemble_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, pinecone_retriever],
        weights=[0.4, 0.6]
    )
    
    # Retrieve documents
    documents = ensemble_retriever.invoke(question)
    
    # Ensure top 10
    documents = documents[:10]
    
    return {"documents": documents}

def rerank(state: GraphState) -> GraphState:
    """
    Reranks documents using a CrossEncoder and keeps the top 4.
    """
    question = state["question"]
    documents = state.get("documents", [])
    
    if not documents:
        return {"documents": []}
    
    # Load CrossEncoder model
    cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    
    # Create pairs of (question, document_text)
    pairs = [[question, doc.page_content] for doc in documents]
    
    # Get scores for each pair
    scores = cross_encoder.predict(pairs)
    
    # Combine documents with their scores and sort descending
    doc_score_pairs = list(zip(documents, scores))
    doc_score_pairs.sort(key=lambda x: x[1], reverse=True)
    
    # Keep top 4 documents
    top_4_docs = [doc for doc, score in doc_score_pairs[:4]]
    
    return {"documents": top_4_docs}

class GradeResult(BaseModel):
    is_relevant: bool = Field(description="True if the document is relevant to the question, False otherwise.")

def grade_documents(state: GraphState) -> GraphState:
    """
    Grades documents for relevance to the question.
    """
    question = state["question"]
    documents = state.get("documents", [])
    retry_count = state.get("retry_count", 0)
    
    if not documents:
        return {"documents": [], "retry_count": retry_count + 1}
    
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    structured_llm = llm.with_structured_output(GradeResult)
    
    prompt = PromptTemplate(
        template="""You are a grader assessing relevance of a retrieved document to a user question.
Here is the retrieved document:
{document}

Here is the user question:
{question}

Assess whether the document is relevant to the question.
""",
        input_variables=["document", "question"],
    )
    
    chain = prompt | structured_llm
    
    relevant_docs = []
    for doc in documents:
        result = chain.invoke({"document": doc.page_content, "question": question})
        if result.is_relevant:
            relevant_docs.append(doc)
            
    if not relevant_docs:
        retry_count += 1
        
    return {"documents": relevant_docs, "retry_count": retry_count}

def decide_after_grading(state: GraphState) -> str:
    """
    Determines whether to generate an answer or rewrite the query.
    """
    documents = state.get("documents", [])
    retry_count = state.get("retry_count", 0)
    
    if not documents and retry_count < 2:
        return "rewrite_query"
    
    return "generate"


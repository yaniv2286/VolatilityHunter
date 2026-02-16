#!/usr/bin/env python3
"""
Code Intelligence Indexer for VolatilityHunter
Builds a semantic search index of the entire codebase for intelligent code navigation
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document

class CodeIndexer:
    """Intelligent code indexer for VolatilityHunter codebase"""
    
    def __init__(self, project_root: str = None):
        """
        Initialize the code indexer
        
        Args:
            project_root: Root directory of the project (defaults to script parent)
        """
        if project_root is None:
            self.project_root = Path(__file__).parent.parent
        else:
            self.project_root = Path(project_root)
        
        self.knowledge_base_dir = self.project_root / ".vh_knowledge_base"
        self.persist_directory = self.knowledge_base_dir / "chroma_db"
        
        # Initialize embeddings model
        self.embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # Initialize text splitter for code
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=[
                "\n\nclass ", "\n\ndef ", "\n\n# ", "\n\n## ", "\n\n### ",
                "\n\n", "\n", " ", ""
            ]
        )
        
        print(f"🧠 Code Intelligence Indexer initialized")
        print(f"📁 Project Root: {self.project_root}")
        print(f"🗄️  Knowledge Base: {self.knowledge_base_dir}")
    
    def find_python_files(self) -> List[Path]:
        """Find all Python files in the project"""
        python_files = []
        
        # Walk through project directory
        for file_path in self.project_root.rglob("*.py"):
            # Skip hidden directories and common exclusions
            if any(part.startswith('.') for part in file_path.parts):
                continue
            if any(part in ['__pycache__', 'node_modules', '.git', 'venv', 'env'] for part in file_path.parts):
                continue
            
            python_files.append(file_path)
        
        print(f"📄 Found {len(python_files)} Python files")
        return sorted(python_files)
    
    def load_code_documents(self, python_files: List[Path]) -> List[Document]:
        """Load and prepare code documents"""
        documents = []
        
        for file_path in python_files:
            try:
                # Read file content
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Create document with metadata
                relative_path = file_path.relative_to(self.project_root)
                doc = Document(
                    page_content=content,
                    metadata={
                        "source": str(relative_path),
                        "file_path": str(file_path),
                        "file_name": file_path.name,
                        "file_size": len(content),
                        "last_modified": file_path.stat().st_mtime
                    }
                )
                documents.append(doc)
                
            except Exception as e:
                print(f"⚠️  Error loading {file_path}: {e}")
        
        print(f"📚 Loaded {len(documents)} code documents")
        return documents
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents into chunks"""
        chunks = self.text_splitter.split_documents(documents)
        
        # Add chunk metadata
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_id"] = i
            chunk.metadata["chunk_count"] = len(chunks)
        
        print(f"🔪 Split into {len(chunks)} chunks")  # Fixed missing closing brace in f-string
        return chunks
    
    def create_index(self, chunks: List[Document]) -> Chroma:
        """Create and persist the vector index"""
        # Create knowledge base directory
        self.knowledge_base_dir.mkdir(exist_ok=True)
        
        # Create vector store
        vector_store = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=str(self.persist_directory)
        )
        
        print(f"💾 Created vector index with {len(chunks)} chunks")
        return vector_store
    
    def build_index(self) -> Chroma:
        """Build the complete code intelligence index"""
        print("="*80)
        print("🧠 VOLATILITYHUNTER CODE INTELLIGENCE INDEXER")
        print("="*80)
        
        # Step 1: Find Python files
        python_files = self.find_python_files()
        
        # Step 2: Load documents
        documents = self.load_code_documents(python_files)
        
        # Step 3: Split into chunks
        chunks = self.split_documents(documents)
        
        # Step 4: Create index
        vector_store = self.create_index(chunks)
        
        print("="*80)
        print("✅ CODE INTELLIGENCE INDEX BUILT SUCCESSFULLY!")
        print(f"📊 Statistics:")
        print(f"   - Python Files: {len(python_files)}")
        print(f"   - Documents: {len(documents)}")
        print(f"   - Chunks: {len(chunks)}")
        print(f"   - Embeddings Model: all-MiniLM-L6-v2")
        print(f"   - Index Location: {self.persist_directory}")
        print("="*80)
        
        return vector_store
    
    def load_existing_index(self) -> Chroma:
        """Load existing index if it exists"""
        if self.persist_directory.exists():
            print(f"📂 Loading existing index from {self.persist_directory}")
            vector_store = Chroma(
                persist_directory=str(self.persist_directory),
                embedding_function=self.embeddings
            )
            return vector_store
        else:
            print(f"🆕 No existing index found at {self.persist_directory}")
            return None
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the index"""
        if not self.persist_directory.exists():
            return {"status": "No index found"}
        
        vector_store = self.load_existing_index()
        if vector_store is None:
            return {"status": "Failed to load index"}
        
        # Get collection info
        collection = vector_store._collection
        count = collection.count()
        
        return {
            "status": "Index loaded",
            "chunks_count": count,
            "persist_directory": str(self.persist_directory),
            "embeddings_model": "all-MiniLM-L6-v2"
        }

def main():
    """Main entry point"""
    indexer = CodeIndexer()
    
    # Check if index already exists
    if indexer.persist_directory.exists():
        print("📂 Existing index found. Rebuilding...")
    
    # Build the index
    vector_store = indexer.build_index()
    
    # Show statistics
    stats = indexer.get_index_stats()
    print(f"\n📊 Index Statistics: {stats}")

if __name__ == "__main__":
    main()

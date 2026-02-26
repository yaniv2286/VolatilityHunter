#!/usr/bin/env python3
"""
Code Intelligence Query Tool for VolatilityHunter
Allows semantic search of the codebase using natural language queries
"""

import os
import os; os.environ['TOKENIZERS_PARALLELISM'] = 'false'
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

class CodeQueryTool:
    """Intelligent code query tool for VolatilityHunter codebase"""
    
    def __init__(self, project_root: str = None):
        """
        Initialize the code query tool
        
        Args:
            project_root: Root directory of the project (defaults to script parent)
        """
        if project_root is None:
            self.project_root = Path(__file__).parent.parent
        else:
            self.project_root = Path(project_root)
        
        self.knowledge_base_dir = self.project_root / ".vh_knowledge_base"
        self.persist_directory = self.knowledge_base_dir / "chroma_db"
        
        # Initialize embeddings model (same as indexer)
        self.embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # Initialize vector store
        self.vector_store = None
        self.qa_chain = None
        
        print(f"🔍 Code Query Tool initialized")
        print(f"📁 Project Root: {self.project_root}")
        print(f"🗄️  Knowledge Base: {self.knowledge_base_dir}")
    
    def load_index(self) -> bool:
        """Load the existing code index"""
        if not self.persist_directory.exists():
            print(f"❌ No index found at {self.persist_directory}")
            print(f"💡 Run 'python scripts/index_codebase.py' first to build the index")
            return False
        
        try:
            print(f"📂 Loading code index from {self.persist_directory}")
            self.vector_store = Chroma(
                persist_directory=str(self.persist_directory),
                embedding_function=self.embeddings
            )
            
            # Get collection info
            collection = self.vector_store._collection
            count = collection.count()
            print(f"✅ Index loaded successfully with {count} chunks")
            return True
            
        except Exception as e:
            print(f"❌ Error loading index: {e}")
            return False
    
    def semantic_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Perform semantic search on the codebase
        
        Args:
            query: Natural language query
            k: Number of results to return
            
        Returns:
            List of relevant code chunks with metadata
        """
        if not self.vector_store:
            print("❌ No index loaded. Call load_index() first.")
            return []
        
        try:
            # Perform similarity search
            results = self.vector_store.similarity_search_with_score(query, k=k)
            
            formatted_results = []
            for doc, score in results:
                formatted_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "similarity_score": score,
                    "source": doc.metadata.get("source", "Unknown"),
                    "file_name": doc.metadata.get("file_name", "Unknown")
                })
            
            return formatted_results
            
        except Exception as e:
            print(f"❌ Error performing search: {e}")
            return []
    
    def format_results(self, results: List[Dict[str, Any]], query: str) -> str:
        """Format search results for display"""
        if not results:
            return f"❌ No results found for query: '{query}'"
        
        output = []
        output.append("="*80)
        output.append(f"🔍 SEARCH RESULTS FOR: '{query}'")
        output.append("="*80)
        
        for i, result in enumerate(results, 1):
            output.append(f"\n📄 RESULT {i}/{len(results)}")
            output.append(f"📁 File: {result['source']}")
            output.append(f"🎯 Similarity: {result['similarity_score']:.4f}")
            output.append(f"📝 Content:")
            
            # Show first 500 characters of content
            content = result['content']
            if len(content) > 500:
                content = content[:500] + "..."
            
            # Add indentation for better readability
            for line in content.split('\n'):
                output.append(f"   {line}")
            
            output.append("-" * 60)
        
        return '\n'.join(output)
    
    def query(self, query: str, k: int = 5, show_results: bool = True) -> List[Dict[str, Any]]:
        """
        Query the codebase with natural language
        
        Args:
            query: Natural language query
            k: Number of results to return
            show_results: Whether to print formatted results
            
        Returns:
            List of search results
        """
        print(f"🔍 Querying codebase: '{query}'")
        
        # Load index if not already loaded
        if not self.vector_store:
            if not self.load_index():
                return []
        
        # Perform search
        results = self.semantic_search(query, k)
        
        # Show results if requested
        if show_results:
            formatted_output = self.format_results(results, query)
            print(formatted_output)
        
        return results
    
    def get_file_overview(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Get overview of a specific file
        
        Args:
            file_path: Relative path to file
            
        Returns:
            List of chunks from the specified file
        """
        # Convert to relative path if absolute
        if os.path.isabs(file_path):
            file_path = os.path.relpath(file_path, self.project_root)
        
        query = f"file:{file_path} content overview"
        return self.query(query, k=10, show_results=False)
    
    def find_function_implementation(self, function_name: str) -> List[Dict[str, Any]]:
        """
        Find implementation of a specific function
        
        Args:
            function_name: Name of the function to find
            
        Returns:
            List of chunks containing the function implementation
        """
        query = f"function {function_name} implementation def {function_name}"
        return self.query(query, k=5, show_results=False)
    
    def find_class_definition(self, class_name: str) -> List[Dict[str, Any]]:
        """
        Find definition of a specific class
        
        Args:
            class_name: Name of the class to find
            
        Returns:
            List of chunks containing the class definition
        """
        query = f"class {class_name} definition"
        return self.query(query, k=5, show_results=False)
    
    def analyze_dependencies(self, component: str) -> List[Dict[str, Any]]:
        """
        Analyze dependencies of a component
        
        Args:
            component: Name of the component (class, function, or file)
            
        Returns:
            List of chunks showing dependencies
        """
        query = f"{component} imports dependencies requires"
        return self.query(query, k=10, show_results=False)

def main():
    """Main entry point for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Query VolatilityHunter codebase')
    parser.add_argument('query', nargs='?', help='Search query')
    parser.add_argument('--file', help='Get overview of specific file')
    parser.add_argument('--function', help='Find function implementation')
    parser.add_argument('--class', dest='class_name', help='Find class definition')
    parser.add_argument('--dependencies', help='Analyze dependencies of component')
    parser.add_argument('--k', type=int, default=5, help='Number of results to return')
    parser.add_argument('--stats', action='store_true', help='Show index statistics')
    
    args = parser.parse_args()
    
    # Initialize query tool
    query_tool = CodeQueryTool()
    
    # Show statistics if requested
    if args.stats:
        if query_tool.load_index():
            collection = query_tool.vector_store._collection
            count = collection.count()
            print(f"📊 Index Statistics:")
            print(f"   - Chunks: {count}")
            print(f"   - Location: {query_tool.persist_directory}")
            print(f"   - Model: all-MiniLM-L6-v2")
        return
    
    # Perform different types of queries
    if args.file:
        results = query_tool.get_file_overview(args.file)
        print(query_tool.format_results(results, f"File overview: {args.file}"))
    elif args.function:
        results = query_tool.find_function_implementation(args.function)
        print(query_tool.format_results(results, f"Function implementation: {args.function}"))
    elif args.class_name:
        results = query_tool.find_class_definition(args.class_name)
        print(query_tool.format_results(results, f"Class definition: {args.class_name}"))
    elif args.dependencies:
        results = query_tool.analyze_dependencies(args.dependencies)
        print(query_tool.format_results(results, f"Dependencies: {args.dependencies}"))
    elif args.query:
        results = query_tool.query(args.query, k=args.k)
    else:
        print("❌ No query specified. Use --help for usage options.")

if __name__ == "__main__":
    main()

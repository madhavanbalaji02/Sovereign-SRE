"""
Codebase Observer
=================
Recursively scans the project, chunks files using SourceCodeNodeParser,
and indexes them in ChromaDB for semantic search.
"""

import os
from pathlib import Path
from typing import Optional
from datetime import datetime

from llama_index.core import Document, VectorStoreIndex, Settings
from llama_index.core.node_parser import CodeSplitter
from llama_index.core.schema import TextNode
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

# =============================================================================
# CONFIGURATION
# =============================================================================

WORKSPACE_PATH = os.environ.get("WORKSPACE_PATH", "/workspace")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
CHROMA_HOST = os.environ.get("CHROMA_HOST", "http://localhost:8000")
EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "bge-m3")
COLLECTION_NAME = os.environ.get("CHROMA_COLLECTION_NAME", "sovereign_sre_codebase")

# File extensions to index
CODE_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".json": "json",
    ".md": "markdown",
    ".sql": "sql",
    ".html": "html",
    ".css": "css",
    ".dockerfile": "dockerfile",
}

# Directories to ignore
IGNORE_DIRS = {
    ".git", "__pycache__", "node_modules", ".next", "venv", ".venv",
    "env", ".env", "dist", "build", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", "eggs", "chroma_data", "ollama_data", ".tox",
    "htmlcov", "coverage", ".idea", ".vscode"
}

# Files to ignore
IGNORE_FILES = {".DS_Store", "Thumbs.db", ".gitignore", ".env", ".env.example"}


# =============================================================================
# CODEBASE OBSERVER
# =============================================================================

class CodebaseObserver:
    """
    Recursively scans a codebase and indexes it in ChromaDB for RAG queries.
    
    Uses BGE-M3 embeddings via Ollama and CodeSplitter for intelligent chunking.
    """
    
    def __init__(
        self,
        workspace_path: Optional[str] = None,
        collection_name: str = COLLECTION_NAME,
        ollama_host: str = OLLAMA_HOST,
        chroma_host: str = CHROMA_HOST,
        embed_model: str = EMBED_MODEL,
    ):
        self.workspace_path = Path(workspace_path or WORKSPACE_PATH)
        self.collection_name = collection_name
        self.ollama_host = ollama_host
        self.chroma_host = chroma_host
        self.embed_model = embed_model
        
        # Initialize components
        self._setup_embedding()
        self._setup_vector_store()
        
    def _setup_embedding(self):
        """Configure the embedding model"""
        self.embed_model_instance = OllamaEmbedding(
            model_name=self.embed_model,
            base_url=self.ollama_host,
        )
        # Set as global default
        Settings.embed_model = self.embed_model_instance
        
    def _setup_vector_store(self):
        """Initialize ChromaDB connection"""
        # Parse host and port from URL
        host = self.chroma_host.replace("http://", "").replace("https://", "")
        if ":" in host:
            host, port = host.split(":")
            port = int(port)
        else:
            port = 8000
        
        self.chroma_client = chromadb.HttpClient(host=host, port=port)
        
        # Get or create collection
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Sovereign-SRE codebase index"}
        )
        
        self.vector_store = ChromaVectorStore(chroma_collection=self.collection)
        
    def _should_index_file(self, file_path: Path) -> bool:
        """Check if a file should be indexed"""
        # Check extension
        if file_path.suffix.lower() not in CODE_EXTENSIONS:
            return False
        
        # Check filename
        if file_path.name in IGNORE_FILES:
            return False
        
        # Check parent directories
        for part in file_path.parts:
            if part in IGNORE_DIRS:
                return False
        
        return True
    
    def _get_language(self, file_path: Path) -> str:
        """Get the language for a file"""
        return CODE_EXTENSIONS.get(file_path.suffix.lower(), "text")
    
    def _read_file_content(self, file_path: Path) -> Optional[str]:
        """Read file content with error handling"""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception as e:
            print(f"⚠️ Could not read {file_path}: {e}")
            return None
    
    def scan_files(self) -> list[Path]:
        """Recursively scan for indexable files"""
        files = []
        
        for root, dirs, filenames in os.walk(self.workspace_path):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            for filename in filenames:
                file_path = Path(root) / filename
                if self._should_index_file(file_path):
                    files.append(file_path)
        
        return files
    
    def create_documents(self, files: list[Path]) -> list[Document]:
        """Create LlamaIndex documents from files"""
        documents = []
        
        for file_path in files:
            content = self._read_file_content(file_path)
            if content is None or not content.strip():
                continue
            
            relative_path = file_path.relative_to(self.workspace_path)
            language = self._get_language(file_path)
            
            doc = Document(
                text=content,
                metadata={
                    "file_path": str(relative_path),
                    "file_name": file_path.name,
                    "language": language,
                    "extension": file_path.suffix,
                    "indexed_at": datetime.utcnow().isoformat(),
                },
            )
            documents.append(doc)
        
        return documents
    
    def chunk_documents(self, documents: list[Document]) -> list[TextNode]:
        """Chunk documents using language-aware splitter"""
        all_nodes = []
        
        # Group documents by language
        by_language: dict[str, list[Document]] = {}
        for doc in documents:
            lang = doc.metadata.get("language", "text")
            if lang not in by_language:
                by_language[lang] = []
            by_language[lang].append(doc)
        
        # Process each language group
        for language, docs in by_language.items():
            try:
                splitter = CodeSplitter(
                    language=language,
                    chunk_lines=40,
                    chunk_lines_overlap=10,
                    max_chars=1500,
                )
                nodes = splitter.get_nodes_from_documents(docs)
                all_nodes.extend(nodes)
            except Exception as e:
                # Fallback for unsupported languages
                print(f"⚠️ CodeSplitter failed for {language}: {e}")
                for doc in docs:
                    # Simple chunking fallback
                    node = TextNode(
                        text=doc.text[:1500],
                        metadata=doc.metadata,
                    )
                    all_nodes.append(node)
        
        return all_nodes
    
    def index_codebase(self, force_reindex: bool = False) -> VectorStoreIndex:
        """
        Main entry point: scan, chunk, and index the codebase.
        
        Args:
            force_reindex: If True, clear existing index before reindexing
            
        Returns:
            VectorStoreIndex ready for querying
        """
        print(f"🔍 Scanning workspace: {self.workspace_path}")
        
        # Check if we should reindex
        if force_reindex:
            print("🗑️ Clearing existing index...")
            try:
                self.chroma_client.delete_collection(self.collection_name)
                self._setup_vector_store()  # Recreate
            except Exception as e:
                print(f"⚠️ Could not clear collection: {e}")
        
        # Scan for files
        files = self.scan_files()
        print(f"📁 Found {len(files)} indexable files")
        
        if not files:
            print("⚠️ No files to index!")
            return VectorStoreIndex.from_vector_store(self.vector_store)
        
        # Create documents
        print("📄 Creating documents...")
        documents = self.create_documents(files)
        print(f"📝 Created {len(documents)} documents")
        
        # Chunk documents
        print("✂️ Chunking documents...")
        nodes = self.chunk_documents(documents)
        print(f"🧩 Created {len(nodes)} chunks")
        
        # Create index
        print("🔢 Generating embeddings and indexing...")
        index = VectorStoreIndex(
            nodes=nodes,
            vector_store=self.vector_store,
            embed_model=self.embed_model_instance,
        )
        
        print(f"✅ Indexing complete! {len(nodes)} chunks indexed.")
        return index
    
    def get_index(self) -> VectorStoreIndex:
        """Get the existing index without reindexing"""
        return VectorStoreIndex.from_vector_store(
            self.vector_store,
            embed_model=self.embed_model_instance,
        )
    
    def get_stats(self) -> dict:
        """Get index statistics"""
        try:
            count = self.collection.count()
            return {
                "collection_name": self.collection_name,
                "chunk_count": count,
                "workspace_path": str(self.workspace_path),
            }
        except Exception as e:
            return {"error": str(e)}


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def main():
    """CLI entry point for indexing"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Index codebase for RAG")
    parser.add_argument("--workspace", "-w", default=WORKSPACE_PATH, help="Workspace path")
    parser.add_argument("--force", "-f", action="store_true", help="Force reindex")
    parser.add_argument("--stats", "-s", action="store_true", help="Show stats only")
    
    args = parser.parse_args()
    
    observer = CodebaseObserver(workspace_path=args.workspace)
    
    if args.stats:
        stats = observer.get_stats()
        print(f"📊 Index Stats: {stats}")
        return
    
    observer.index_codebase(force_reindex=args.force)


if __name__ == "__main__":
    main()

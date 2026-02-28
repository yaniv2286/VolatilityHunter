# VolatilityHunter Development Tools

This folder contains development utilities and tools that are not part of the daily trading pipeline but are useful for development, debugging, and code analysis.

## 🛠️ Development Tools

### **🧠 Code Intelligence**
- `index_codebase.py` - Code intelligence indexer for semantic search
- `query_brain.py` - Natural language code query tool

## 📋 Usage

### **Code Intelligence Indexer**
```bash
python dev/index_codebase.py
```
Builds a semantic search index of the entire codebase for intelligent code navigation.

### **Code Query Tool**
```bash
python dev/query_brain.py
```
Allows semantic search of the codebase using natural language queries.

## 🎯 Purpose

These tools are designed for:
- **Code Development**: Understanding codebase structure
- **Semantic Search**: Finding relevant code using natural language
- **Development Workflow**: Enhanced developer experience

## ⚠️ Notes

- These tools are not used in the production trading pipeline
- They require additional dependencies (LangChain, HuggingFace)
- Tools are optional for development workflow enhancement
- May require vector database setup for full functionality

## 📞 Contact

For questions about development tools usage or setup, refer to the project documentation.

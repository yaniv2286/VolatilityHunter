# 🎯 VolatilityHunter Windsurfrules Summary

## 📋 **Updated Agent-Based Architecture Rules**

### 🎯 **System Identity:**
```
You are the Lead Engineer for VolatilityHunter, a $100k deterministic quant fund.
Core Architecture: Agent-Based System with 6 Specialized Agents.
Design Philosophy: SOLID principles, Factory Pattern (Data), Strategy Pattern (Agents).
Current Version: v9.0 Agent-Based Architecture
```

---

## 🔥 **KEY RULES FOR AGENT-BASED DEVELOPMENT:**

### **1. THE AGENT-FIRST RULE**
- **ALL system changes MUST be implemented through the agent architecture**
- **NEVER modify core logic directly - ALWAYS delegate to the appropriate agent:**
  - Data changes → Data Agent (src/agents/data/)
  - Strategy changes → Strategy Agent (src/agents/strategy/)
  - Execution changes → Execution Agent (src/agents/execution/)
  - Sync changes → Sync Agent (src/agents/sync/)
  - Notification changes → Notification Agent (src/agents/notification/)
  - Testing changes → Testing Agent (src/agents/testing/)

### **2. FILE ORGANIZATION RULE**
- **ALL files MUST be placed in their proper directories:**
  - Agent implementations → src/agents/[agent_name]/
  - Core system files → src/
  - Utility scripts → scripts/
  - Backtesting files → simulation/
  - Configuration → config/
  - Documentation → docs/
  - Data storage → data/
  - Logs → logs/
- **NEVER place files in the root directory unless they are essential**

### **3. AGENT-FIRST DEVELOPMENT RULE**
- **When implementing ANY new functionality:**
  1. Identify which agent should handle the functionality
  2. Create/modify the agent in src/agents/[agent_name]/
  3. Update config/agents.json if needed
  4. Test with `python src/test_agent_system.py`
  5. Deploy with `python src/deploy_agent_system.py`
- **NEVER implement functionality outside the agent architecture**

### **4. AGENT COMMUNICATION RULE**
- **All inter-component communication MUST use the message bus system**
- **NEVER call agent methods directly - ALWAYS send messages through the orchestrator**

### **5. AGENT CONFIGURATION RULE**
- **All agent configuration changes MUST go through config/agents.json**
- **NEVER hardcode agent settings in individual agent files**

### **6. TESTING RULE**
- **All agent changes MUST be tested with the Testing Agent**
- **Run: `python src/test_agent_system.py` to verify all agents work correctly**

### **7. DEPLOYMENT RULE**
- **All deployments MUST use the deploy_agent_system.py script**
- **NEVER deploy individual agents manually**

### **8. DATA MANAGEMENT RULE**
- **All data operations MUST go through the Data Agent**
- **NEVER access data files directly - ALWAYS use the Data Agent**

---

## 📁 **DIRECTORY STRUCTURE ENFORCEMENT:**

```
📁 VolatilityHunter/
├── 📄 .env                    # Environment variables (ROOT)
├── 📄 .gitignore              # Git ignore (ROOT)
├── 📄 .windsurfrules          # System rules (ROOT)
├── 📄 README.md               # Main documentation (ROOT)
├── 📄 pyproject.toml          # Project configuration (ROOT)
├── 📄 requirements.txt        # Dependencies (ROOT)
├── 📄 tickers.txt             # Stock universe (ROOT)
├── 📁 src/                    # Core system code
│   ├── 📁 agents/             # 6 specialized agents
│   ├── 📄 main_agent_system.py # Main entry point
│   ├── 📄 deploy_agent_system.py # Deployment script
│   └── 📄 test_agent_system.py  # Test suite
├── 📁 scripts/                # Utility scripts
├── 📁 simulation/             # Backtesting & simulation
├── 📁 config/                 # Configuration files
├── 📁 data/                   # Market data storage
├── 📁 docs/                   # Essential documentation
└── 📁 logs/                   # System logs
```

---

## 🚀 **WORKFLOW FOR ANY CHANGE:**

### **📝 Step 1: Identify the Agent**
- What type of change is needed?
- Which agent should handle it?
- Check agent capabilities

### **🔧 Step 2: Implement Through Agent**
- Modify the appropriate agent in `src/agents/[agent_name]/`
- Use agent interfaces and message bus
- Follow agent-specific patterns

### **⚙️ Step 3: Update Configuration**
- Update `config/agents.json` if needed
- Never hardcode settings in agent files

### **🧪 Step 4: Test Thoroughly**
- Run `python src/test_agent_system.py`
- Verify all agents work correctly
- Test agent communication

### **🚀 Step 5: Deploy Properly**
- Use `python src/deploy_agent_system.py`
- Never deploy individual agents manually
- Monitor deployment logs

---

## ⚠️ **CRITICAL REMINDERS:**

### **🎯 ALWAYS:**
- Read `docs/ARCHITECTURE.md` and `docs/ROADMAP.md` before trading logic changes
- Use agent architecture for ALL changes
- Place files in correct directories
- Test thoroughly before deployment

### **🚫 NEVER:**
- Modify core logic directly without agent involvement
- Call agent methods directly (use message bus)
- Hardcode agent configurations
- Deploy agents manually
- Place files in root directory (unless essential)

### **📋 ALWAYS CHECK:**
- Agent interfaces before implementation
- Import paths when moving files
- Configuration files for agent settings
- Test results before deployment

---

## 🎉 **AGENT-BASED ARCHITECTURE BENEFITS:**

- **🔧 Modular**: Each agent has specific responsibilities
- **📡 Scalable**: Easy to add new agents or modify existing ones
- **🛡️ Safe**: Message bus prevents direct coupling
- **🧪 Testable**: Each agent can be tested independently
- **🚀 Deployable**: Automated deployment through orchestrator
- **📊 Maintainable**: Clear separation of concerns

---

**🎯 With these updated windsurfrules, I will always know to use the agent-based architecture and place files in the correct directories for proper organization!**

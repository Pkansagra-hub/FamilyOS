# Developer Workflow Guide
## How to Develop MemoryOS with the Contract System

**Version:** 1.1.0
**Last Updated:** September 12, 2025
**Audience:** All Developers
**Status:** Production Ready ✅

---

## 🎯 **TL;DR - How Development Works Now**

**Good News:** 90% of your development stays exactly the same! The contract system works in the background to protect you from breaking things.

**When You Need Contracts:** Only when you're changing how different parts of the app communicate with each other.

---

## 🤔 **What Are Contracts?**

Think of contracts as the **"rules"** that keep your app's parts working together:

- **📡 API Contracts** - What URLs your app responds to and what data format they expect
- **📬 Event Contracts** - Messages different parts of your app send to each other
- **💾 Storage Contracts** - How your app saves and loads data
- **🔒 Policy Contracts** - Security and privacy rules

**Example:** If the memory system expects emotion data in a specific format, that's defined in a contract. If you change the format, you update the contract so other parts know what changed.

---

## 📅 **Daily Development Scenarios**

### 🟢 **Scenario 1: Regular Feature Development (90% of work)**

**What you're doing:**
- Adding new functions to existing modules
- Fixing bugs in Python code
- Improving algorithms or performance
- Adding new calculations or logic

**Your workflow:**
```bash
# Just code like normal!
code .                                    # Open VS Code
# Edit your Python files in api/, core/, storage/, etc.
# Write tests in tests/
# Commit when ready
git add .
git commit -m "feat: improve emotion detection accuracy"
git push
```

**What the system does:**
- ✅ Automatically validates your code follows existing contracts
- ✅ Runs tests to ensure nothing breaks
- ✅ Lets you know if you accidentally changed a contract

**Result:** Your PR gets approved automatically if everything looks good!

---

### 🟡 **Scenario 2: Adding New API Endpoints**

**What you're doing:**
- Adding new REST API endpoints (like `GET /api/memories/search`)
- Users or other apps will call these endpoints

**Your workflow:**
```bash
# Step 1: Use the automation helper
python scripts/contracts/contract_helper.py new-endpoint

# This will ask you questions like:
# - What's the endpoint path? (e.g., /api/memories/search)
# - What HTTP method? (GET, POST, etc.)
# - What data does it return?

# Step 2: The helper creates all the contract files for you
# - Updates contracts/api/openapi/main.yaml
# - Creates example requests/responses
# - Sets up validation rules

# Step 3: Implement your Python code
# Edit api/routers/memories.py (or wherever)
def search_memories(query: str):
    # Your implementation here
    pass

# Step 4: Write tests and commit everything
```

**What the system does:**
- ✅ Validates your API contract is correct
- ✅ Ensures your Python code matches the contract
- ✅ Checks that other parts of the app can still work

---

### 🟠 **Scenario 3: Changing Data Storage**

**What you're doing:**
- Adding new fields to database records
- Changing how data is structured
- Adding new types of data storage

**Your workflow:**
```bash
# Step 1: Check what you're changing
python scripts/contracts/contract_helper.py validate

# Step 2: Use the schema helper
python scripts/contracts/contract_helper.py new-schema

# This will guide you through:
# - What data structure you're changing
# - What fields you're adding/removing
# - Whether this breaks existing data

# Step 3: Update the contracts
# The helper shows you exactly which files to edit:
# - contracts/storage/schemas/your_schema.schema.json
# - contracts/storage/examples/your_schema.example.json

# Step 4: Validate your changes
python scripts/contracts/storage_validate.py

# Step 5: Implement your Python storage code
# Edit storage/your_store.py

# Step 6: Create a contract freeze
python scripts/contracts/contracts_freeze.py create v1.2.0-add-memory-tags
```

**What the system does:**
- ✅ Validates your schema changes won't break existing data
- ✅ Creates migration plans if needed
- ✅ Ensures all parts of the app know about the changes

---

### 🔴 **Scenario 4: Adding Cross-Module Communication**

**What you're doing:**
- Making one part of the app send messages to another part
- Adding new event types or data flows

**Your workflow:**
```bash
# Step 1: Use the event helper
python scripts/contracts/contract_helper.py new-event

# This will ask:
# - What's the event name? (e.g., emotion_detected)
# - What data does it carry?
# - Which modules send/receive it?

# Step 2: The helper creates event contracts
# - Updates contracts/events/schemas/
# - Updates contracts/events/topics.yaml
# - Creates example events

# Step 3: Implement sending the event
# In your Python code:
from events.bus import EventBus
bus.publish(Event(
    meta=EventMeta(topic="emotions", type="emotion_detected"),
    payload={"emotion": "happy", "confidence": 0.85}
))

# Step 4: Implement receiving the event
async def handle_emotion(event):
    emotion = event.payload["emotion"]
    # Your handling code here

bus.subscribe("emotions", "my_module", handle_emotion)
```

---

## 🛠️ **Development Tools Available**

### **🤖 Automation Helper**
```bash
python scripts/contracts/contract_helper.py
```
**Commands:**
- `new-endpoint` - Add new API endpoint with contracts
- `new-schema` - Add new data storage schema
- `new-event` - Add new cross-module event
- `validate` - Check if your changes are valid
- `bump-version` - Update version numbers correctly

### **🔍 Validation Tools**
```bash
# Check all contracts are valid
python scripts/contracts/storage_validate.py

# Check event contracts
python scripts/contracts/check_envelope_invariants.py

# Run contract tests
python -m ward test --path tests/ --pattern "*contract*"
```

### **📸 Version Control**
```bash
# Save current contract state
python scripts/contracts/contracts_freeze.py create v1.2.0-my-feature

# See all saved versions
python scripts/contracts/contracts_freeze.py list

# Restore if something breaks
python scripts/contracts/contracts_freeze.py restore v1.1.0-stable
```

---

## 🚦 **What Happens When You Push Code**

### **✅ Automatic Checks (GitHub Actions)**
When you create a pull request, the system automatically:

1. **Contract Validation** - Ensures your contracts are properly formatted
2. **Breaking Change Detection** - Warns if you're about to break something
3. **Test Execution** - Runs all tests to ensure nothing breaks
4. **Version Validation** - Checks that version numbers follow rules
5. **Documentation Check** - Ensures documentation is updated

### **🔴 If Something's Wrong**
You'll get clear error messages like:
```
❌ Contract validation failed
→ Field 'user_id' is required but missing from example
→ Fix: Add user_id to contracts/storage/examples/memory.example.json

❌ Breaking change detected
→ Removing field 'created_at' will break existing clients
→ Fix: Mark field as deprecated instead of removing
```

### **✅ If Everything's Good**
Your PR gets approved and you can merge!

---

## 🎓 **Learning Path**

### **👶 New to the Codebase**
1. Read this guide (you're doing it!)
2. Try adding a simple function (Scenario 1)
3. Look at `contracts/CONTRACT_CHANGE_QUICK_REF.md` for commands
4. Ask for help when you need contract changes

### **🧑‍💻 Regular Developer**
1. Master the automation helper: `python scripts/contracts/contract_helper.py`
2. Understand the quick reference: `contracts/CONTRACT_CHANGE_QUICK_REF.md`
3. Learn to read contract validation errors
4. Know how to restore when things break

### **👨‍🏫 Senior Developer**
1. Read the full process: `contracts/CONTRACT_CHANGE_PROCESS.md`
2. Understand version management and breaking changes
3. Know how to guide others through contract changes
4. Help with emergency procedures and rollbacks

---

## 🆘 **When Things Go Wrong**

### **😰 "I broke something and don't know how to fix it"**
```bash
# This restores to the last known good state
python scripts/contracts/contracts_freeze.py restore v1.1.0-comprehensive-docs

# Then validate everything is working
python scripts/contracts/storage_validate.py
```

### **🤔 "CI is failing and I don't understand why"**
1. Look at the error message - it usually tells you exactly what to fix
2. Run validation locally: `python scripts/contracts/storage_validate.py`
3. Ask for help with the specific error message

### **😵 "I need to make a change but don't know what type it is"**
```bash
# This will analyze your changes and guide you
python scripts/contracts/contract_helper.py validate
```

### **🔥 "Production is broken and I need to rollback"**
```bash
# Emergency rollback procedure
python scripts/contracts/contracts_freeze.py list  # Find stable version
python scripts/contracts/contracts_freeze.py restore v1.1.0-stable
# Redeploy with stable contracts
```

---

## 📊 **Contract Change Decision Tree**

```
Do you need to change how parts of the app talk to each other?
│
├─ NO → Just code normally (Scenario 1)
│   ├─ Add functions to existing files
│   ├─ Fix bugs
│   ├─ Improve algorithms
│   └─ ✅ No contract changes needed
│
└─ YES → What are you changing?
    │
    ├─ Adding API endpoint → Scenario 2
    │   └─ Use: python scripts/contracts/contract_helper.py new-endpoint
    │
    ├─ Changing data storage → Scenario 3
    │   └─ Use: python scripts/contracts/contract_helper.py new-schema
    │
    ├─ Adding events/messages → Scenario 4
    │   └─ Use: python scripts/contracts/contract_helper.py new-event
    │
    └─ Not sure? → Get help
        └─ Use: python scripts/contracts/contract_helper.py validate
```

---

## 🔄 **Example: Complete Feature Development**

Let's say you want to add a "memory tagging" feature:

### **Step 1: Plan the Feature**
```
What am I building?
- Users can add tags to memories (like #family, #vacation)
- New API endpoint to add/remove tags
- Store tags in the database
- Send events when tags change
```

### **Step 2: Identify Contract Changes**
```
- New API endpoint: POST /api/memories/{id}/tags ✅
- New storage field: memories.tags ✅
- New event: memory_tagged ✅
```

### **Step 3: Use Automation**
```bash
# Add the API endpoint
python scripts/contracts/contract_helper.py new-endpoint
# → Follow prompts for POST /api/memories/{id}/tags

# Add storage field
python scripts/contracts/contract_helper.py new-schema
# → Follow prompts to add tags field to memory schema

# Add event
python scripts/contracts/contract_helper.py new-event
# → Follow prompts for memory_tagged event
```

### **Step 4: Implement Python Code**
```python
# api/routers/memories.py
@router.post("/memories/{memory_id}/tags")
async def add_memory_tag(memory_id: str, tag: str):
    # Your implementation
    memory = await memory_store.add_tag(memory_id, tag)
    await event_bus.publish(Event(
        meta=EventMeta(topic="memories", type="memory_tagged"),
        payload={"memory_id": memory_id, "tag": tag}
    ))
    return {"success": True}

# storage/memory_store.py
async def add_tag(self, memory_id: str, tag: str):
    # Your storage implementation
    pass
```

### **Step 5: Test and Deploy**
```bash
# Validate everything
python scripts/contracts/storage_validate.py

# Run tests
python -m ward test

# Create contract freeze
python scripts/contracts/contracts_freeze.py create v1.2.0-memory-tagging

# Commit and push
git add .
git commit -m "feat: add memory tagging system"
git push
```

**Result:** Your feature is complete with proper contracts, validation, and version control!

---

## 🎯 **Key Principles**

### **🛡️ Safety First**
- The contract system prevents you from accidentally breaking things
- All changes are validated before they reach production
- Easy rollback if something goes wrong

### **🚀 Developer Experience**
- Automation handles the complex parts
- Clear error messages when something's wrong
- Most development stays exactly the same

### **📈 Incremental Adoption**
- Start with simple scenarios (just coding)
- Learn contract changes as you need them
- Advanced features available when you're ready

### **🤝 Team Coordination**
- Contracts ensure everyone's changes work together
- Clear documentation of what changed and when
- Automatic validation prevents conflicts

---

## 🎉 **Summary**

**The contract system is designed to help you, not slow you down.**

- **90% of development** stays exactly the same
- **Automation tools** guide you through contract changes
- **Safety nets** prevent breaking production
- **Clear documentation** for when you need help

**Bottom line:** Focus on building great features. The contract system handles the complexity of keeping everything working together.

---

## 📚 **Quick Reference Links**

- **Daily commands:** `contracts/CONTRACT_CHANGE_QUICK_REF.md`
- **Complete process:** `contracts/CONTRACT_CHANGE_PROCESS.md`
- **Directory overview:** `contracts/README.md`
- **Implementation status:** `contracts/CONTRACT_IMPLEMENTATION_COMPLETE.md`

**Questions?** The automation helper is your friend: `python scripts/contracts/contract_helper.py`

---

**Happy coding! The contracts have your back.** 🚀

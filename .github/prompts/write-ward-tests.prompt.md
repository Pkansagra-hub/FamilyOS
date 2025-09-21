````prompt
# 🧪 Ward Test Development Prompts

Use these prompts when creating comprehensive Ward tests following MemoryOS testing standards.

---

## 📝 **Create Ward Tests for Module**

```
I need to create Ward tests for code changes following MemoryOS testing requirements:

**Module Context:**
- **Changed Modules:** [List specific modules/files that changed]
- **Change Type:** [New feature/Bug fix/Refactor/Performance improvement]
- **Test Coverage Required:** [Unit/Integration/Contract/Performance tests needed]
- **Business Logic:** [What functionality needs testing]

**Testing Requirements:**
- **Unit Tests:** ≥70% coverage of touched logic
- **Integration Tests:** All changed I/O paths
- **Contract Tests:** Schema and event validation
- **Performance Tests:** Hot path validation if applicable

**Test Structure:**
Mirror module layout under `tests/` directory:
- Module: `src/module/service.py` → Test: `tests/module/test_service.py`
- Follow Ward testing framework conventions
- Use WARD (Write-Arrange-Run-Deliver) pattern

**Coverage Areas:**
1. **Unit Testing:**
   - Core business logic functions
   - Edge cases and error conditions
   - Input validation and sanitization
   - State management and transitions

2. **Integration Testing:**
   - Database interactions
   - Event bus communications
   - External service calls
   - Cross-module dependencies

3. **Contract Testing:**
   - API schema validation
   - Event envelope compliance
   - Storage contract adherence
   - Policy enforcement verification

4. **Performance Testing:**
   - Hot path latency requirements
   - Memory usage patterns
   - Throughput benchmarks
   - Resource utilization limits

**Implementation Steps:**
1. Create test files mirroring module structure
2. Write comprehensive test cases
3. Ensure proper fixtures and test data
4. Add performance benchmarks for hot paths
5. Run test suite and validate coverage

**Validation Commands:**
- Run VS Code task: `tests:ward`
- Fallback: `poetry run python -m ward -p tests`
- Check coverage: `poetry run python -m ward -p tests --coverage`

**Acceptance Criteria:**
- [ ] Unit tests cover ≥70% of touched logic
- [ ] Integration tests validate all I/O paths
- [ ] Contract tests ensure schema compliance
- [ ] Performance tests meet SLO requirements
- [ ] All tests pass without failures
- [ ] Test structure mirrors module layout
- [ ] Proper fixtures and test data setup
- [ ] No mock theater (real component testing)

Please help me create comprehensive Ward tests for the changed modules.
```

---

## 🔧 **Test Debugging & Fixes**

```
I'm having issues with Ward test failures or coverage:

**Test Issue Details:**
- **Failing Tests:** [List specific test failures]
- **Error Messages:** [Detailed error output]
- **Coverage Gaps:** [Areas lacking sufficient coverage]
- **Performance Issues:** [Tests running too slowly]

**Module Context:**
- **Code Under Test:** [Which modules are being tested]
- **Test Files:** [Corresponding test file paths]
- **Dependencies:** [External dependencies or fixtures]
- **Test Environment:** [Local/CI/specific configuration]

**Debugging Information:**
- **Test Output:** [Full Ward test output]
- **Stack Traces:** [Detailed error traces]
- **Coverage Report:** [Current coverage percentages]
- **Recent Changes:** [What changed since tests last passed]

**Common Issues:**
- Test isolation problems
- Fixture setup/teardown issues
- Async/await handling
- Database state management
- Mock usage (avoid mock theater)

Please help me debug and fix the Ward test issues.
```

---

## 📊 **Test Coverage Analysis**

```
I need to analyze and improve test coverage for specific modules:

**Coverage Analysis Request:**
- **Target Modules:** [Modules requiring coverage improvement]
- **Current Coverage:** [Existing coverage percentages]
- **Coverage Goals:** [Target coverage levels]
- **Critical Paths:** [Most important code paths to cover]

**Coverage Gaps:**
- **Untested Functions:** [Functions without test coverage]
- **Edge Cases:** [Boundary conditions not tested]
- **Error Paths:** [Exception handling not covered]
- **Integration Points:** [Cross-module interactions not tested]

**Improvement Plan:**
1. Identify high-impact untested code
2. Create targeted test cases
3. Add edge case and error condition tests
4. Improve integration test coverage
5. Validate business logic thoroughly

**Quality Metrics:**
- Line coverage percentage
- Branch coverage percentage
- Function coverage percentage
- Integration path coverage

Please help me analyze coverage gaps and create a plan to achieve comprehensive testing.
```
````

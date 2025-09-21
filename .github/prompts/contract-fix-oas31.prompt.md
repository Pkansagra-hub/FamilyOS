````prompt
# 🔧 OpenAPI 3.1 & JSON Schema 2020-12 Alignment Prompts

Use these prompts when fixing API contracts to comply with OpenAPI 3.1 and JSON Schema 2020-12 standards.

---

## ⚡ **Fix OAS 3.1 Compliance Issues**

```
I need to fix API contracts to pass lint & bundle by aligning OpenAPI 3.1 with JSON Schema 2020-12:

**Current Issues:**
- **Lint Errors:** [List specific linting errors]
- **Bundle Failures:** [Bundle generation problems]
- **Schema Compliance:** [JSON Schema 2020-12 issues]
- **Reference Problems:** [Broken $ref paths or external references]

**Contract Files:**
- **Main API Spec:** `contracts/api/openapi/main.yaml`
- **Envelope Schema:** `contracts/events/envelope.schema.json`
- **Target Output:** `contracts/api/openapi.v1.yaml`

**Compliance Requirements:**
1. **OpenAPI 3.1 Header Upgrade:**
   ```yaml
   openapi: 3.1.0
   jsonSchemaDialect: https://json-schema.org/draft/2020-12/schema
   ```

2. **Reference Path Fixes:**
   - Envelope schema under `components.schemas.Envelope`:
     ```yaml
     externalDocs:
       url: ../../events/envelope.schema.json
     allOf:
       - $ref: '../../events/envelope.schema.json'
     ```
   - Use forward slashes for all paths
   - Ensure all $ref paths resolve correctly

3. **Security Implementation:**
   - Define security schemes:
     ```yaml
     securitySchemes:
       mtls:
         type: mutualTLS
       bearer:
         type: http
         scheme: bearer
     ```
   - Add global security: `security: [{ mtls: [] }, { bearer: [] }]`
   - Exempt health endpoints: `security: []` for `/v1/healthz` and `/v1/readyz`

4. **4xx Response Coverage:**
   - Add missing 4xx responses to all operations:
     - `400: { $ref: '#/components/responses/BadRequest' }`
     - `401: { $ref: '#/components/responses/Unauthorized' }`
     - `403: { $ref: '#/components/responses/Forbidden' }`
     - `429: { $ref: '#/components/responses/TooManyRequests' }`
   - Reuse existing Problem response components

5. **Metadata Quality Improvements:**
   - Add `info.license` field
   - Add descriptive `tags[].description` for every tag
   - Ensure complete API documentation

6. **JSON Schema 2020-12 Features:**
   - Allow `contentEncoding`, `$schema`, `$id`, `$defs`
   - Support `if/then/else` conditional logic
   - Enable `type: ["string","null"]` nullable types
   - No downgrades from modern schema features

**Implementation Process:**
1. **Upgrade OpenAPI Header:**
   - Set version to 3.1.0
   - Configure JSON Schema dialect

2. **Fix Reference Paths:**
   - Update all $ref paths to use forward slashes
   - Ensure external references resolve correctly
   - Test bundle generation

3. **Implement Security:**
   - Define mutual TLS and bearer token schemes
   - Apply global security requirements
   - Exempt health check endpoints

4. **Add Missing Responses:**
   - Identify operations lacking 4xx responses
   - Add standard error responses
   - Reuse existing component definitions

5. **Enhance Metadata:**
   - Complete license information
   - Add tag descriptions
   - Improve overall documentation

6. **Validate & Bundle:**
   ```bash
   npx @redocly/cli@latest lint contracts/api/openapi/main.yaml
   npx @redocly/cli@latest bundle contracts/api/openapi/main.yaml -o contracts/api/openapi.v1.yaml
   ```

7. **Contract Validation:**
   - Run VS Code task: `contracts:validate`
   - Fallback: `python scripts/contracts/storage_validate.py`

**Constraints & Guardrails:**
- **DO NOT** auto-edit `.env*`, lockfiles, or `.vscode/*.json` without approval
- **PREFER** additive changes over breaking modifications
- **STOP** if breaking changes are unavoidable and invoke Contract Freeze & Migration
- **KEEP** health endpoints unauthenticated
- **ENSURE** all business endpoints have security requirements

**Acceptance Criteria:**
- [ ] Redocly lint passes with 0 errors (warnings acceptable)
- [ ] Bundle generation succeeds without errors
- [ ] `contracts:validate` exits with code 0
- [ ] `openapi.v1.yaml` generated successfully
- [ ] All $ref paths resolve correctly
- [ ] Security properly implemented
- [ ] 4xx responses added to all operations
- [ ] JSON Schema 2020-12 compliance achieved
- [ ] No breaking changes introduced

**Deliverables:**
- Fixed `contracts/api/openapi/main.yaml`
- Generated `contracts/api/openapi.v1.yaml`
- Before/after linter statistics
- Small PR with change summary

Please help me fix the OpenAPI 3.1 compliance issues and generate a clean bundled specification.
```

---

## 🔍 **Schema Reference Troubleshooting**

```
I'm having issues with schema references and external file resolution:

**Reference Problems:**
- **Broken $ref Paths:** [List failing reference paths]
- **External File Issues:** [Problems with external schema files]
- **Bundle Failures:** [Reference resolution during bundling]
- **Circular References:** [Potential circular dependency issues]

**File Structure:**
- **Main OpenAPI:** [Path to main specification]
- **Referenced Schemas:** [List of external schema files]
- **Output Target:** [Where bundled file should be generated]

**Error Details:**
- **Lint Output:** [Specific linter error messages]
- **Bundle Errors:** [Bundle command error output]
- **File Paths:** [Current reference paths being used]

Please help me diagnose and fix the schema reference issues.
```

---

## 🛡️ **Security Scheme Implementation**

```
I need help implementing proper security schemes in OpenAPI 3.1:

**Security Requirements:**
- **Authentication Methods:** [mTLS/Bearer/API Key/etc.]
- **Global Security:** [Default security applied to all endpoints]
- **Exemptions:** [Endpoints that should bypass security]
- **Authorization Scopes:** [If using OAuth or similar]

**Current Implementation:**
- **Existing Security:** [What's currently defined]
- **Problems:** [Issues with current security setup]
- **Missing Elements:** [Security schemes not yet implemented]

**Configuration Needs:**
- Security scheme definitions
- Global security application
- Per-endpoint security overrides
- Documentation and examples

Please help me implement comprehensive API security following OpenAPI 3.1 standards.
```
````

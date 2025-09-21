````prompt
# 🔒 API Security & Error Response Prompts

Use these prompts when adding security posture and 4xx error responses to OpenAPI specifications.

---

## 🛡️ **Add Security & 4xx Responses**

```
I need to add security definitions and 4xx error responses to satisfy linter requirements:

**Current Issue:**
- **Linter Errors:** [List specific linter errors like "operation-4xx-response" or "security-defined"]
- **OpenAPI File:** [Path to the OpenAPI specification]
- **Operations Missing 4xx:** [List endpoints that need error responses]
- **Security Context:** [What security scheme is needed]

**Security Requirements:**
- Add global security scheme: `security: [ { mtls: [] }, { bearer: [] } ]`
- Exempt health endpoints: `/v1/healthz` and `/v1/readyz` with `security: []`
- Ensure proper authentication for all business endpoints

**4xx Response Requirements:**
For each operation missing 4xx responses, add:
- `400: { $ref: '#/components/responses/BadRequest' }` - Invalid request format
- `401: { $ref: '#/components/responses/Unauthorized' }` - Authentication required
- `403: { $ref: '#/components/responses/Forbidden' }` - Access denied
- `429: { $ref: '#/components/responses/TooManyRequests' }` - Rate limiting

**Component References:**
If response components aren't defined, create them under `components.responses` using the existing `Problem` schema.

**Validation Steps:**
1. Apply security and 4xx response changes
2. Run: `npx @redocly/cli@latest lint contracts/api/openapi/main.yaml`
3. Run: `npx @redocly/cli@latest bundle contracts/api/openapi/main.yaml -o contracts/api/openapi.v1.yaml`
4. Validate with: `python scripts/contracts/storage_validate.py`

**Acceptance Criteria:**
- [ ] No "operation-4xx-response" linter errors
- [ ] No "security-defined" linter errors
- [ ] All business endpoints have proper security
- [ ] Health endpoints are exempt from security
- [ ] Lint passes with 0 errors
- [ ] Bundle generation succeeds
- [ ] Contract validation passes

Please help me implement these security and error response requirements without changing business logic.
```

---

## 🔧 **Security Troubleshooting**

```
I'm having issues with API security implementation:

**Problem Details:**
- **Error Messages:** [Specific security-related errors]
- **Current Security Scheme:** [What's currently implemented]
- **Authentication Method:** [mTLS/Bearer/API Key/etc.]
- **Affected Endpoints:** [Which endpoints have issues]

**Troubleshooting Context:**
- **Recent Changes:** [What was modified recently]
- **Environment:** [Dev/Staging/Prod]
- **Security Requirements:** [Specific security needs]

Please help me diagnose and fix the security implementation issues.
```
````es & Security Posture

Goal: Satisfy linter rules requiring 4xx responses and security, without changing business logic.

Steps:
1) Add `security: [ { mtls: [] }, { bearer: [] } ]` at root.
2) For `/v1/healthz` and `/v1/readyz`, set `security: []`.
3) For each operation missing 4xx, add:
   - `400: { $ref: '#/components/responses/BadRequest' }`
   - `401: { $ref: '#/components/responses/Unauthorized' }`
   - `403: { $ref: '#/components/responses/Forbidden' }`
   - `429: { $ref: '#/components/responses/TooManyRequests' }`
4) If response components aren’t defined, create them once under `components.responses` using the existing `Problem` schema.
5) Lint & bundle; update PR.

Acceptance:
- No “operation-4xx-response” or “security-defined” errors.

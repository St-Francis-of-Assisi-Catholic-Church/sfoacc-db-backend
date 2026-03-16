from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>SFOACC API — Frontend Integration Guide</title>
<style>
  :root {
    --bg: #0f1117;
    --surface: #181c27;
    --surface2: #1e2333;
    --border: #2a3045;
    --accent: #4f8ef7;
    --accent2: #7c3aed;
    --green: #22c55e;
    --red: #ef4444;
    --yellow: #f59e0b;
    --text: #e2e8f0;
    --muted: #8892a4;
    --code-bg: #141820;
    --sidebar-w: 268px;
    --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    --mono: "JetBrains Mono", "Fira Code", "Cascadia Code", Menlo, monospace;
  }
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html { scroll-behavior: smooth; font-size: 15px; }
  body { background: var(--bg); color: var(--text); font-family: var(--font); display: flex; min-height: 100vh; }

  /* ── Sidebar ──────────────────────────────────────────────── */
  nav#sidebar {
    width: var(--sidebar-w); min-width: var(--sidebar-w);
    height: 100vh; position: sticky; top: 0; overflow-y: auto;
    background: var(--surface); border-right: 1px solid var(--border);
    padding: 0 0 2rem; display: flex; flex-direction: column;
  }
  .nav-logo { padding: 1.25rem 1.25rem 1rem; border-bottom: 1px solid var(--border); margin-bottom: 0.5rem; }
  .nav-logo h1 { font-size: 1rem; font-weight: 700; color: var(--accent); letter-spacing: -0.01em; }
  .nav-logo span { font-size: 0.75rem; color: var(--muted); }
  .nav-section-label {
    font-size: 0.65rem; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: var(--muted);
    padding: 0.9rem 1.25rem 0.3rem;
  }
  nav#sidebar a {
    display: block; padding: 0.35rem 1.25rem 0.35rem 1.5rem;
    color: var(--muted); text-decoration: none; font-size: 0.85rem;
    border-left: 2px solid transparent; transition: all 0.15s;
  }
  nav#sidebar a:hover, nav#sidebar a.active {
    color: var(--text); border-left-color: var(--accent); background: rgba(79,142,247,0.07);
  }

  /* ── Main content ──────────────────────────────────────────── */
  main { flex: 1; min-width: 0; padding: 2.5rem clamp(1.5rem, 5vw, 4rem) 5rem; max-width: 900px; }
  section { margin-bottom: 4rem; scroll-margin-top: 1.5rem; }

  h2 { font-size: 1.6rem; font-weight: 700; margin-bottom: 1rem; color: #fff;
       border-bottom: 1px solid var(--border); padding-bottom: 0.6rem; }
  h3 { font-size: 1.1rem; font-weight: 600; margin: 1.75rem 0 0.6rem; color: #d0d8e8; }
  h4 { font-size: 0.9rem; font-weight: 600; margin: 1.2rem 0 0.4rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }
  p  { line-height: 1.75; color: #b0bcd0; margin-bottom: 0.75rem; }
  ul, ol { padding-left: 1.4rem; margin-bottom: 0.75rem; }
  li { line-height: 1.75; color: #b0bcd0; margin-bottom: 0.2rem; }
  strong { color: var(--text); }
  code { font-family: var(--mono); font-size: 0.82em; background: var(--code-bg);
         border: 1px solid var(--border); border-radius: 4px; padding: 0.15em 0.4em; color: #a5f3fc; }

  /* ── Code blocks ───────────────────────────────────────────── */
  .code-block { position: relative; margin: 1rem 0 1.25rem; border-radius: 8px;
                border: 1px solid var(--border); overflow: hidden; }
  .code-block-header {
    display: flex; align-items: center; justify-content: space-between;
    background: var(--surface2); padding: 0.4rem 0.85rem;
    font-size: 0.75rem; color: var(--muted); border-bottom: 1px solid var(--border);
  }
  .code-block-header .lang { color: var(--accent); font-family: var(--mono); font-weight: 600; }
  .copy-btn {
    background: none; border: 1px solid var(--border); border-radius: 4px;
    color: var(--muted); font-size: 0.72rem; padding: 0.2rem 0.55rem;
    cursor: pointer; transition: all 0.15s;
  }
  .copy-btn:hover { color: var(--text); border-color: var(--accent); }
  pre { background: var(--code-bg); padding: 1rem 1.1rem; overflow-x: auto;
        font-family: var(--mono); font-size: 0.82rem; line-height: 1.7; }
  pre .c  { color: #64748b; }   /* comment */
  pre .k  { color: #a78bfa; }   /* keyword */
  pre .s  { color: #86efac; }   /* string */
  pre .n  { color: #93c5fd; }   /* name / property */
  pre .t  { color: #f0abfc; }   /* type */
  pre .v  { color: #fbbf24; }   /* value / number */
  pre .op { color: #e2e8f0; }   /* operator / punctuation */

  /* ── Tables ─────────────────────────────────────────────────── */
  .table-wrap { overflow-x: auto; margin: 1rem 0 1.5rem; border-radius: 8px;
                border: 1px solid var(--border); }
  table { width: 100%; border-collapse: collapse; font-size: 0.84rem; }
  th { background: var(--surface2); color: var(--muted); font-weight: 600;
       text-align: left; padding: 0.55rem 1rem; border-bottom: 1px solid var(--border);
       font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }
  td { padding: 0.5rem 1rem; border-bottom: 1px solid var(--border); color: #b0bcd0; vertical-align: top; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: rgba(255,255,255,0.02); }
  td code { font-size: 0.8em; }

  /* ── Badges ─────────────────────────────────────────────────── */
  .badge { display: inline-block; font-size: 0.68rem; font-weight: 700; font-family: var(--mono);
           padding: 0.18em 0.55em; border-radius: 4px; letter-spacing: 0.03em; }
  .badge-get    { background: rgba(34,197,94,0.15);  color: #4ade80; border: 1px solid rgba(34,197,94,0.3); }
  .badge-post   { background: rgba(79,142,247,0.15); color: #7eb8ff; border: 1px solid rgba(79,142,247,0.3); }
  .badge-put    { background: rgba(245,158,11,0.15); color: #fbbf24; border: 1px solid rgba(245,158,11,0.3); }
  .badge-delete { background: rgba(239,68,68,0.15);  color: #f87171; border: 1px solid rgba(239,68,68,0.3); }
  .badge-patch  { background: rgba(168,85,247,0.15); color: #c084fc; border: 1px solid rgba(168,85,247,0.3); }

  /* ── Endpoint rows ───────────────────────────────────────────── */
  .endpoint { display: flex; align-items: baseline; gap: 0.75rem; margin: 0.55rem 0; }
  .endpoint .path { font-family: var(--mono); font-size: 0.83rem; color: var(--text); }
  .endpoint .desc { color: var(--muted); font-size: 0.82rem; }

  /* ── Callout boxes ───────────────────────────────────────────── */
  .callout { border-left: 3px solid var(--accent); background: rgba(79,142,247,0.07);
             border-radius: 0 6px 6px 0; padding: 0.75rem 1rem; margin: 1rem 0 1.25rem; }
  .callout.warn  { border-color: var(--yellow); background: rgba(245,158,11,0.07); }
  .callout.tip   { border-color: var(--green);  background: rgba(34,197,94,0.07); }
  .callout p { margin: 0; font-size: 0.85rem; }
  .callout strong { color: inherit; }

  /* ── Model cards ─────────────────────────────────────────────── */
  .model-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px,1fr)); gap: 0.75rem; margin: 1rem 0 1.5rem; }
  .model-card { background: var(--surface2); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; }
  .model-card h4 { margin: 0 0 0.4rem; color: var(--accent); font-size: 0.85rem; text-transform: none; letter-spacing: 0; }
  .model-card p { font-size: 0.78rem; margin: 0; }

  /* ── Scrollbar ───────────────────────────────────────────────── */
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
</style>
</head>
<body>

<!-- ─── Sidebar ─────────────────────────────────────────────────────────────── -->
<nav id="sidebar">
  <div class="nav-logo">
    <h1>SFOACC API</h1>
    <span>Frontend Integration Guide</span>
  </div>

  <div class="nav-section-label">Getting Started</div>
  <a href="#overview">Overview</a>
  <a href="#quickstart">Quick Start</a>
  <a href="#auth">Authentication</a>
  <a href="#auth-otp">OTP / Passwordless</a>
  <a href="#response-format">Response Format</a>
  <a href="#pagination">Pagination</a>
  <a href="#errors">Error Handling</a>

  <div class="nav-section-label">Data Models</div>
  <a href="#model-church-unit">Church Units</a>
  <a href="#model-parishioner">Parishioners</a>
  <a href="#model-society">Societies</a>
  <a href="#model-community">Communities</a>
  <a href="#model-user">Users &amp; RBAC</a>
  <a href="#model-roles">Groups &amp; Scoping</a>

  <div class="nav-section-label">API Endpoints</div>
  <a href="#ep-auth">Auth</a>
  <a href="#ep-parish">Parish</a>
  <a href="#ep-parishioners">Parishioners</a>
  <a href="#ep-societies">Societies</a>
  <a href="#ep-communities">Communities</a>
  <a href="#ep-users">Users</a>
  <a href="#ep-admin">Admin</a>

  <div class="nav-section-label">SDK</div>
  <a href="#sdk-setup">Setup</a>
  <a href="#sdk-client">Client</a>
  <a href="#sdk-hooks">React Query Hooks</a>
  <a href="#sdk-examples">Examples</a>

  <div class="nav-section-label">Reference</div>
  <a href="#enums">Enums &amp; Constants</a>
  <a href="#permissions">Permissions</a>
  <a href="#swagger">Swagger / OpenAPI</a>
</nav>

<!-- ─── Main ─────────────────────────────────────────────────────────────────── -->
<main>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<section id="overview">
<h2>Overview</h2>
<p>
  The <strong>SFOACC API</strong> is the backend for the <strong>St. Francis of Assisi Catholic Church
  (Ashaley Botwe)</strong> parish management system. It provides a full REST API for managing parishioners,
  societies, mass schedules, church communities, user accounts, and access control.
</p>

<div class="model-grid">
  <div class="model-card">
    <h4>Runtime</h4>
    <p>FastAPI 0.110+ · Python 3.11+</p>
  </div>
  <div class="model-card">
    <h4>Database</h4>
    <p>PostgreSQL 15 · SQLAlchemy 2 ORM</p>
  </div>
  <div class="model-card">
    <h4>Auth</h4>
    <p>JWT Bearer · Password or OTP (SMS/email) · Role-based permissions</p>
  </div>
  <div class="model-card">
    <h4>Base URL</h4>
    <p><code>/api/v1</code></p>
  </div>
</div>

<h3>High-level architecture</h3>
<p>
  Everything is organised around <strong>ChurchUnit</strong> — a single unified model that represents either
  the <em>Parish</em> (St. Francis of Assisi) or an <em>Outstation</em> (e.g. St. Andrews, Nanakrom).
  All other resources — parishioners, societies, church communities, users — belong to a church unit
  via <code>church_unit_id</code>.
</p>

<div class="code-block">
  <div class="code-block-header"><span class="lang">text — entity relationship</span></div>
  <pre>ChurchUnit (Parish)
  ├── ChurchUnit (Outstation)   ← parent_id references Parish
  │     ├── MassSchedule[]
  │     ├── Society[]
  │     └── ChurchCommunity[]
  ├── MassSchedule[]
  ├── Society[]
  ├── ChurchCommunity[]
  ├── Parishioner[]             ← church_unit_id
  └── User[]                   ← church_unit_id (scope)</pre>
</div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<section id="quickstart">
<h2>Quick Start</h2>

<h3>1 — Login and get a token</h3>
<div class="code-block">
  <div class="code-block-header"><span class="lang">bash</span><button class="copy-btn">copy</button></div>
  <pre><span class="c"># POST /api/v1/auth/login  (form-encoded, NOT JSON)</span>
curl -X POST https://yourapi.com/api/v1/auth/login \
  -d <span class="s">"username=admin@example.com&amp;password=YourPassword"</span></pre>
</div>

<div class="code-block">
  <div class="code-block-header"><span class="lang">json — response</span></div>
  <pre>{
  <span class="n">"access_token"</span>: <span class="s">"eyJhbGciOiJIUzI1NiIs..."</span>,
  <span class="n">"token_type"</span>: <span class="s">"bearer"</span>,
  <span class="n">"user"</span>: { <span class="n">"id"</span>: <span class="s">"uuid"</span>, <span class="n">"email"</span>: <span class="s">"..."</span>, <span class="n">"role"</span>: <span class="s">"super_admin"</span>, <span class="op">...</span> }
}</pre>
</div>

<h3>2 — Use the token</h3>
<div class="code-block">
  <div class="code-block-header"><span class="lang">bash</span><button class="copy-btn">copy</button></div>
  <pre>curl https://yourapi.com/api/v1/parish \
  -H <span class="s">"Authorization: Bearer &lt;access_token&gt;"</span></pre>
</div>

<div class="callout tip">
  <p><strong>Tip:</strong> The <code>/api/v1/docs</code> page provides interactive Swagger UI — useful for exploring
  and testing endpoints directly in the browser.</p>
</div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<section id="auth">
<h2>Authentication</h2>

<p>
  The API supports <strong>multiple login methods</strong>, all returning the same JWT Bearer token.
  Which methods are enabled is controlled by the super admin via <code>PUT /api/v1/admin/settings/auth</code>.
</p>

<div class="table-wrap">
<table>
  <tr><th>Method</th><th>Endpoint</th><th>Body type</th><th>Default</th></tr>
  <tr><td>Password</td><td><code>POST /api/v1/auth/login</code></td><td><code>application/x-www-form-urlencoded</code></td><td>✓ enabled</td></tr>
  <tr><td>OTP (email + SMS)</td><td><code>POST /api/v1/auth/otp/request</code> → <code>/otp/verify</code></td><td>JSON</td><td>disabled</td></tr>
</table>
</div>

<p>Every request (after login) must include:</p>
<div class="code-block">
  <div class="code-block-header"><span class="lang">http</span></div>
  <pre>Authorization: Bearer &lt;access_token&gt;</pre>
</div>

<h3>Password login</h3>
<div class="code-block">
  <div class="code-block-header"><span class="lang">bash</span><button class="copy-btn">copy</button></div>
  <pre><span class="c"># form-encoded, NOT JSON — username field = email address</span>
curl -X POST /api/v1/auth/login \
  -d <span class="s">"username=admin@example.com&amp;password=YourPassword"</span></pre>
</div>

<div class="code-block">
  <div class="code-block-header"><span class="lang">json — response</span></div>
  <pre>{
  <span class="n">"access_token"</span>: <span class="s">"eyJhbGciOiJIUzI1NiIs..."</span>,
  <span class="n">"token_type"</span>: <span class="s">"bearer"</span>,
  <span class="n">"user"</span>: { <span class="n">"id"</span>: <span class="s">"uuid"</span>, <span class="n">"email"</span>: <span class="s">"..."</span>, <span class="n">"role"</span>: <span class="s">"super_admin"</span>, <span class="op">...</span> }
}</pre>
</div>

<h3>New user flow (password)</h3>
<ol>
  <li>Admin creates user via <code>POST /api/v1/user-management</code> — a temporary password is emailed automatically</li>
  <li>User logs in with temp password; status is <code>reset_required</code></li>
  <li>User calls <code>POST /api/v1/auth/reset-password</code> with <code>temp_password</code> + <code>new_password</code></li>
  <li>Status changes to <code>active</code> and a fresh token is returned</li>
</ol>

<div class="callout warn">
  <p><strong>Note:</strong> Users with status <code>reset_required</code> are blocked on all endpoints except
  <code>/auth/reset-password</code> and <code>/auth/otp/verify</code>.</p>
</div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<section id="auth-otp">
<h2>OTP / Passwordless Login</h2>

<p>
  When OTP login is enabled by the super admin, users can log in without a password.
  The flow is two steps: <strong>request</strong> a code, then <strong>verify</strong> it.
  One code is generated and sent to <strong>every available channel at once</strong> — email
  and/or SMS — so the user simply uses whichever arrives first.
</p>

<h3>Step 1 — Request a code</h3>
<div class="code-block">
  <div class="code-block-header"><span class="lang">bash</span><button class="copy-btn">copy</button></div>
  <pre>POST /api/v1/auth/otp/request
Content-Type: application/json

{
  <span class="n">"identifier"</span>: <span class="s">"user@example.com"</span>   <span class="c">// email OR phone with country code (e.g. 233543460633)</span>
}</pre>
</div>

<p>
  The backend looks up the user by email or phone, generates one code, and dispatches it to
  all enabled channels simultaneously (email if <code>otp_email_enabled</code>, SMS if
  <code>otp_sms_enabled</code> and user has a phone number).
  Always returns <code>202</code> regardless of whether the account exists (anti-enumeration).
</p>

<h3>Step 2 — Verify the code</h3>
<div class="code-block">
  <div class="code-block-header"><span class="lang">bash</span><button class="copy-btn">copy</button></div>
  <pre>POST /api/v1/auth/otp/verify
Content-Type: application/json

{
  <span class="n">"identifier"</span>: <span class="s">"user@example.com"</span>,   <span class="c">// or phone number</span>
  <span class="n">"code"</span>:       <span class="s">"482910"</span>
}</pre>
</div>

<p>On success, returns the same <code>{ access_token, token_type, user }</code> envelope as password login.</p>

<div class="table-wrap">
<table>
  <tr><th>Behaviour</th><th>Detail</th></tr>
  <tr><td>Code length</td><td>6 digits (configurable via <code>auth.otp_code_length</code>)</td></tr>
  <tr><td>Expiry</td><td>10 minutes (configurable via <code>auth.otp_expiry_minutes</code>)</td></tr>
  <tr><td>Storage</td><td>SHA-256 hash only — raw code is never persisted</td></tr>
  <tr><td>One-time use</td><td>Code is invalidated on first successful verify</td></tr>
  <tr><td>Previous codes</td><td>All prior unused codes voided when a new one is requested</td></tr>
  <tr><td>Multi-channel</td><td>Same code sent to email + SMS — user uses whichever arrives first</td></tr>
  <tr><td>SMS</td><td>Only sent if <code>otp_sms_enabled = true</code> and user has a phone number</td></tr>
</table>
</div>

<h3>Configure login methods (super admin)</h3>
<div class="code-block">
  <div class="code-block-header"><span class="lang">bash</span><button class="copy-btn">copy</button></div>
  <pre>PUT /api/v1/admin/settings/auth
Authorization: Bearer &lt;super_admin_token&gt;

{
  <span class="n">"password_enabled"</span>:   <span class="k">true</span>,
  <span class="n">"otp_email_enabled"</span>:  <span class="k">true</span>,
  <span class="n">"otp_sms_enabled"</span>:    <span class="k">true</span>,
  <span class="n">"otp_expiry_minutes"</span>: <span class="v">10</span>,
  <span class="n">"otp_code_length"</span>:    <span class="v">6</span>
}</pre>
</div>

<div class="callout warn">
  <p><strong>Warning:</strong> Disabling all login methods will lock everyone out. Requires
  <code>admin:auth_config</code> permission (super admin only).</p>
</div>

<h3>React example — OTP login form</h3>
<div class="code-block">
  <div class="code-block-header"><span class="lang">tsx</span><button class="copy-btn">copy</button></div>
  <pre><span class="k">import</span> { api } <span class="k">from</span> <span class="s">"@/lib/api"</span>;

<span class="k">const</span> [step, setStep] = useState&lt;<span class="t">"request" | "verify"</span>&gt;(<span class="s">"request"</span>);

<span class="c">// Step 1 — just pass email or phone, backend sends to all channels</span>
<span class="k">async function</span> requestCode(identifier: <span class="t">string</span>) {
  <span class="k">await</span> api.requestOtp(identifier);
  setStep(<span class="s">"verify"</span>);
}

<span class="c">// Step 2 — same identifier, enter the code from email or SMS</span>
<span class="k">async function</span> verifyCode(identifier: <span class="t">string</span>, code: <span class="t">string</span>) {
  <span class="k">const</span> res = <span class="k">await</span> api.verifyOtp(identifier, code);
  localStorage.setItem(<span class="s">"token"</span>, res.access_token);
  navigate(<span class="s">"/dashboard"</span>);
}</pre>
</div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<section id="response-format">
<h2>Response Format</h2>

<p>All endpoints return a consistent envelope:</p>

<div class="code-block">
  <div class="code-block-header"><span class="lang">typescript</span></div>
  <pre><span class="k">interface</span> <span class="t">APIResponse</span>&lt;<span class="t">T</span>&gt; {
  <span class="n">message</span>: <span class="t">string</span>;   <span class="c">// human-readable status</span>
  <span class="n">data</span>:    <span class="t">T</span> | <span class="k">null</span>; <span class="c">// the payload</span>
}</pre>
</div>

<p>List endpoints return a paginated payload inside <code>data</code>:</p>

<div class="code-block">
  <div class="code-block-header"><span class="lang">typescript</span></div>
  <pre><span class="k">interface</span> <span class="t">PagedData</span>&lt;<span class="t">T</span>&gt; {
  <span class="n">items</span>: <span class="t">T</span>[];
  <span class="n">total</span>: <span class="t">number</span>;  <span class="c">// total matching records</span>
  <span class="n">skip</span>:  <span class="t">number</span>;  <span class="c">// offset used</span>
  <span class="n">limit</span>: <span class="t">number</span>;  <span class="c">// page size used</span>
}</pre>
</div>

<h3>Example</h3>
<div class="code-block">
  <div class="code-block-header"><span class="lang">json</span></div>
  <pre>{
  <span class="n">"message"</span>: <span class="s">"Retrieved 20 parishioners"</span>,
  <span class="n">"data"</span>: {
    <span class="n">"items"</span>: [ <span class="op">...</span> ],
    <span class="n">"total"</span>: <span class="v">583</span>,
    <span class="n">"skip"</span>:  <span class="v">0</span>,
    <span class="n">"limit"</span>: <span class="v">20</span>
  }
}</pre>
</div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<section id="pagination">
<h2>Pagination</h2>
<p>All list endpoints support <strong>offset-based pagination</strong> via query params:</p>

<div class="table-wrap">
<table>
  <tr><th>Param</th><th>Default</th><th>Max</th><th>Description</th></tr>
  <tr><td><code>skip</code></td><td><code>0</code></td><td>—</td><td>Number of records to skip</td></tr>
  <tr><td><code>limit</code></td><td><code>100</code></td><td><code>1000</code> (parishioners)</td><td>Records to return</td></tr>
</table>
</div>

<div class="code-block">
  <div class="code-block-header"><span class="lang">bash — page 2, 20 per page</span><button class="copy-btn">copy</button></div>
  <pre>GET /api/v1/parishioners/all?skip=20&amp;limit=20</pre>
</div>

<h3>React Query pagination example</h3>
<div class="code-block">
  <div class="code-block-header"><span class="lang">tsx</span><button class="copy-btn">copy</button></div>
  <pre><span class="k">const</span> [page, setPage] = useState(<span class="v">0</span>);
<span class="k">const</span> PAGE_SIZE = <span class="v">20</span>;

<span class="k">const</span> { data } = useParishioners(client, {
  skip:  page * PAGE_SIZE,
  limit: PAGE_SIZE,
});
<span class="c">// data.items  — current page records
// data.total  — total for "Page 3 of 30" display
// data.skip   — echoed back</span>

<span class="k">const</span> totalPages = Math.ceil((data?.total ?? <span class="v">0</span>) / PAGE_SIZE);</pre>
</div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<section id="errors">
<h2>Error Handling</h2>

<div class="table-wrap">
<table>
  <tr><th>Status</th><th>Meaning</th><th>When</th></tr>
  <tr><td><code>400</code></td><td>Bad Request</td><td>Invalid input, duplicate record</td></tr>
  <tr><td><code>401</code></td><td>Unauthorized</td><td>Missing or expired token</td></tr>
  <tr><td><code>403</code></td><td>Forbidden</td><td>Valid token but insufficient permission</td></tr>
  <tr><td><code>404</code></td><td>Not Found</td><td>Resource doesn't exist</td></tr>
  <tr><td><code>409</code></td><td>Conflict</td><td>Duplicate (e.g. duplicate church ID)</td></tr>
  <tr><td><code>422</code></td><td>Validation Error</td><td>Request body fails Pydantic validation</td></tr>
  <tr><td><code>429</code></td><td>Rate Limited</td><td>Too many login attempts</td></tr>
  <tr><td><code>500</code></td><td>Internal Error</td><td>Unexpected server error</td></tr>
</table>
</div>

<p>Error bodies always contain <code>detail</code>:</p>
<div class="code-block">
  <div class="code-block-header"><span class="lang">json</span></div>
  <pre>{ <span class="n">"detail"</span>: <span class="s">"Parishioner not found"</span> }

<span class="c">// 422 includes the full validation breakdown:</span>
{
  <span class="n">"detail"</span>: <span class="s">"Validation Error"</span>,
  <span class="n">"errors"</span>: [{ <span class="n">"loc"</span>: [<span class="s">"body"</span>, <span class="s">"first_name"</span>], <span class="n">"msg"</span>: <span class="s">"..."</span>, <span class="n">"type"</span>: <span class="s">"..."</span> }]
}</pre>
</div>

<div class="code-block">
  <div class="code-block-header"><span class="lang">tsx — handle in React Query</span><button class="copy-btn">copy</button></div>
  <pre><span class="k">const</span> mutation = useCreateParishioner(client);

mutation.mutate(data, {
  onError: (err: APIError) =&gt; {
    <span class="c">// err.status  → HTTP status code</span>
    <span class="c">// err.message → detail string</span>
    toast.error(err.message);
  }
});</pre>
</div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<section id="model-church-unit">
<h2>Model: Church Unit</h2>
<p>
  <strong>ChurchUnit</strong> is the core organisational entity. A single self-referential table
  stores both the <em>Parish</em> and its <em>Outstations</em> (differentiated by <code>type</code>).
</p>

<div class="table-wrap">
<table>
  <tr><th>Field</th><th>Type</th><th>Notes</th></tr>
  <tr><td><code>id</code></td><td><code>number</code></td><td>Auto-increment PK</td></tr>
  <tr><td><code>type</code></td><td><code>"PARISH" | "OUTSTATION"</code></td><td>Enum — determines role</td></tr>
  <tr><td><code>parent_id</code></td><td><code>number | null</code></td><td>For outstations, references the parish</td></tr>
  <tr><td><code>name</code></td><td><code>string</code></td><td>e.g. "St. Francis of Assisi" / "St. Andrews"</td></tr>
  <tr><td><code>address</code></td><td><code>string | null</code></td><td>Physical address</td></tr>
  <tr><td><code>pastor_name / phone / email</code></td><td><code>string | null</code></td><td>Parish pastor info</td></tr>
  <tr><td><code>priest_in_charge / priest_phone</code></td><td><code>string | null</code></td><td>Outstation priest info</td></tr>
  <tr><td><code>latitude / longitude</code></td><td><code>number | null</code></td><td>GPS coordinates</td></tr>
  <tr><td><code>google_maps_url</code></td><td><code>string | null</code></td><td>Maps link</td></tr>
  <tr><td><code>is_active</code></td><td><code>boolean</code></td><td>Soft disable flag</td></tr>
  <tr><td><code>mass_schedules</code></td><td><code>MassSchedule[]</code></td><td>Populated in detail responses</td></tr>
  <tr><td><code>societies</code></td><td><code>SocietySummary[]</code></td><td>Populated in detail responses</td></tr>
  <tr><td><code>communities</code></td><td><code>CommunitySummary[]</code></td><td>Populated in detail responses</td></tr>
  <tr><td><code>outstations</code></td><td><code>OutstationDetail[]</code></td><td>Parish only — all child outstations</td></tr>
</table>
</div>

<h3>MassSchedule</h3>
<div class="table-wrap">
<table>
  <tr><th>Field</th><th>Type</th><th>Notes</th></tr>
  <tr><td><code>day_of_week</code></td><td><code>DayOfWeek</code></td><td>SUNDAY … SATURDAY</td></tr>
  <tr><td><code>time</code></td><td><code>string</code></td><td>ISO time, e.g. <code>"07:30:00"</code></td></tr>
  <tr><td><code>mass_type</code></td><td><code>"SUNDAY"|"WEEKDAY"|"VIGIL"|"SPECIAL"</code></td><td></td></tr>
  <tr><td><code>language</code></td><td><code>string</code></td><td>Default: <code>"English"</code></td></tr>
  <tr><td><code>is_active</code></td><td><code>boolean</code></td><td></td></tr>
</table>
</div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<section id="model-parishioner">
<h2>Model: Parishioner</h2>
<p>
  Central record for a registered member of the parish. IDs are UUIDs.
  The <strong>list</strong> endpoint (<code>GET /parishioners/all</code>) returns the flat
  <code>Parishioner</code> type. The <strong>detail</strong> endpoint (<code>GET /parishioners/:id</code>)
  returns the rich <code>ParishionerDetailed</code> type with all sub-resources loaded.
</p>

<div class="table-wrap">
<table>
  <tr><th>Field</th><th>Type</th><th>Notes</th></tr>
  <tr><td><code>id</code></td><td><code>string (UUID)</code></td><td>System-generated</td></tr>
  <tr><td><code>old_church_id</code></td><td><code>string | null</code></td><td>Legacy 5-digit numeric ID</td></tr>
  <tr><td><code>new_church_id</code></td><td><code>string | null</code></td><td>Generated format: <code>KN3001-00045</code></td></tr>
  <tr><td><code>first_name</code></td><td><code>string</code></td><td>Required</td></tr>
  <tr><td><code>last_name</code></td><td><code>string</code></td><td>Required</td></tr>
  <tr><td><code>gender</code></td><td><code>"male"|"female"|"other"</code></td><td>Required</td></tr>
  <tr><td><code>date_of_birth</code></td><td><code>string | null</code></td><td>ISO date <code>"YYYY-MM-DD"</code></td></tr>
  <tr><td><code>membership_status</code></td><td><code>"active"|"deceased"|"disabled"</code></td><td></td></tr>
  <tr><td><code>verification_status</code></td><td><code>"unverified"|"verified"|"pending"</code></td><td></td></tr>
  <tr><td><code>church_unit_id</code></td><td><code>number | null</code></td><td>Which outstation/parish they belong to</td></tr>
  <tr><td><code>church_community_id</code></td><td><code>number | null</code></td><td>Small group / community cell</td></tr>
</table>
</div>

<h3>ParishionerDetailed (additional fields)</h3>
<div class="table-wrap">
<table>
  <tr><th>Field</th><th>Type</th></tr>
  <tr><td><code>occupation</code></td><td><code>{ role, employer } | null</code></td></tr>
  <tr><td><code>family_info</code></td><td><code>FamilyInfo | null</code> — spouse, parents, children</td></tr>
  <tr><td><code>emergency_contacts</code></td><td><code>EmergencyContact[]</code></td></tr>
  <tr><td><code>medical_conditions</code></td><td><code>MedicalCondition[]</code></td></tr>
  <tr><td><code>sacraments</code></td><td><code>Sacrament[]</code> — baptism, confirmation, etc.</td></tr>
  <tr><td><code>skills</code></td><td><code>Skill[]</code></td></tr>
  <tr><td><code>societies</code></td><td><code>ParishionerSociety[]</code> — with membership date and status</td></tr>
  <tr><td><code>languages_spoken</code></td><td><code>Array&lt;{ id, name, description }&gt;</code></td></tr>
  <tr><td><code>church_unit</code></td><td><code>ChurchUnit | null</code></td></tr>
  <tr><td><code>church_community</code></td><td><code>ChurchCommunity | null</code></td></tr>
</table>
</div>

<h3>Available filters on GET /parishioners/all</h3>
<div class="code-block">
  <div class="code-block-header"><span class="lang">bash</span><button class="copy-btn">copy</button></div>
  <pre>GET /api/v1/parishioners/all
  ?search=John            <span class="c"># name / church ID search</span>
  &amp;church_unit_id=2       <span class="c"># filter by outstation</span>
  &amp;society_id=5           <span class="c"># members of a specific society</span>
  &amp;church_community_id=3
  &amp;gender=male
  &amp;marital_status=married
  &amp;membership_status=active
  &amp;verification_status=verified
  &amp;birth_month=12
  &amp;has_old_church_id=true
  &amp;skip=0&amp;limit=20</pre>
</div>

<h3>Church ID generation</h3>
<p>
  Format: <code>&lt;F_initial&gt;&lt;L_initial&gt;&lt;DD&gt;&lt;MM&gt;-&lt;old_id_padded&gt;</code><br/>
  Example: <code>KN3001-00045</code> (Kwame Nkrumah, born 30 Jan, old ID 45)
</p>
<div class="code-block">
  <div class="code-block-header"><span class="lang">bash</span></div>
  <pre>POST /api/v1/parishioners/{id}/generate-church-id
  ?old_church_id=45
  &amp;send_sms=true</pre>
</div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<section id="model-society">
<h2>Model: Society</h2>
<p>
  Societies (e.g. Catholic Women Association, Knights of St. John) belong to a
  <code>ChurchUnit</code>. Each has members (parishioners) and leadership roles.
</p>

<div class="table-wrap">
<table>
  <tr><th>Field</th><th>Type</th><th>Notes</th></tr>
  <tr><td><code>id</code></td><td><code>number</code></td><td></td></tr>
  <tr><td><code>name</code></td><td><code>string</code></td><td></td></tr>
  <tr><td><code>meeting_frequency</code></td><td><code>"weekly"|"biweekly"|"monthly"|"quarterly"|"annually"</code></td><td></td></tr>
  <tr><td><code>meeting_day</code></td><td><code>string | null</code></td><td>e.g. <code>"Sunday"</code></td></tr>
  <tr><td><code>meeting_time</code></td><td><code>string | null</code></td><td>ISO time</td></tr>
  <tr><td><code>meeting_venue</code></td><td><code>string | null</code></td><td></td></tr>
  <tr><td><code>church_unit_id</code></td><td><code>number | null</code></td><td></td></tr>
  <tr><td><code>members_count</code></td><td><code>number</code></td><td>Computed on read</td></tr>
  <tr><td><code>leadership</code></td><td><code>SocietyLeadership[]</code></td><td>Roles: president, secretary, etc.</td></tr>
</table>
</div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<section id="model-community">
<h2>Model: Church Community</h2>
<p>Small geographic/neighbourhood cells within the parish. Parishioners are assigned to one community.</p>

<div class="table-wrap">
<table>
  <tr><th>Field</th><th>Type</th></tr>
  <tr><td><code>id</code></td><td><code>number</code></td></tr>
  <tr><td><code>name</code></td><td><code>string</code></td></tr>
  <tr><td><code>description</code></td><td><code>string | null</code></td></tr>
  <tr><td><code>location</code></td><td><code>string | null</code></td></tr>
</table>
</div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<section id="model-user">
<h2>Model: User &amp; RBAC</h2>
<p>
  System users (admins, outstation secretaries, etc.) are separate from parishioners.
  Each user has a <strong>Role</strong> which carries a set of <strong>Permission</strong> codes.
</p>

<div class="table-wrap">
<table>
  <tr><th>Field</th><th>Type</th><th>Notes</th></tr>
  <tr><td><code>id</code></td><td><code>string (UUID)</code></td><td></td></tr>
  <tr><td><code>email</code></td><td><code>string</code></td><td>Used as login username</td></tr>
  <tr><td><code>full_name</code></td><td><code>string</code></td><td></td></tr>
  <tr><td><code>phone</code></td><td><code>string | null</code></td><td>Required for OTP SMS delivery</td></tr>
  <tr><td><code>role</code></td><td><code>string | null</code></td><td>Role name, e.g. <code>"super_admin"</code></td></tr>
  <tr><td><code>role_label</code></td><td><code>string | null</code></td><td>Human-readable label</td></tr>
  <tr><td><code>church_unit_id</code></td><td><code>number | null</code></td><td>Scopes the user to one unit (outstation admins)</td></tr>
  <tr><td><code>status</code></td><td><code>"active"|"inactive"|"reset_required"</code></td><td></td></tr>
</table>
</div>

<p>
  <strong>church_unit_id on a User</strong> acts as a permission scope: if set, all data-access queries
  are automatically restricted to that church unit. Global admins (super_admin) have <code>null</code>.
</p>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<section id="model-roles">
<h2>Groups &amp; Data Scoping</h2>

<p>
  RBAC works in two layers: <strong>permission codes</strong> control what actions a user can perform,
  and <strong>church_unit_id</strong> on the User row controls which data they see.
  Groups (called <em>roles</em> internally) are scoped to a church unit and can be shared across multiple users.
  Super admins can create additional custom groups at any time.
</p>

<h3>Built-in groups</h3>
<div class="table-wrap">
<table>
  <tr><th>Group name</th><th>Scope</th><th>Description</th></tr>
  <tr><td><code>super_admin</code></td><td>Global</td><td><code>admin:all</code> — bypasses all permission checks. Not scoped to any church unit.</td></tr>
  <tr><td><code>church_administrator</code></td><td>Own unit only</td><td>Manages all operations for their assigned church unit — parishioners, societies, users, mass schedules, and settings.</td></tr>
  <tr><td><code>church_secretary</code></td><td>Own unit only</td><td>Handles parishioner records, church ID generation, and correspondence for their assigned church unit.</td></tr>
  <tr><td><code>church_finance_admin</code></td><td>Own unit only</td><td>Manages financial records and reports. Read-only access to parishioner data.</td></tr>
</table>
</div>

<h3>How data scoping works in code</h3>
<p>
  When a user has a <code>church_unit_id</code> set, the <code>ChurchUnitScope</code> dependency in
  the API automatically filters all queries to only that unit. The frontend does not need to send
  <code>church_unit_id</code> as a filter — it is enforced server-side.
</p>

<div class="code-block">
  <div class="code-block-header"><span class="lang">text — scoping examples</span></div>
  <pre>User: church_administrator, church_unit_id = 3 (St. Andrews)

GET /api/v1/parishioners/all  →  only returns St. Andrews parishioners
GET /api/v1/societies/all     →  only returns St. Andrews societies
POST /api/v1/societies        →  new society auto-assigned to unit 3

User: super_admin, church_unit_id = null

GET /api/v1/parishioners/all  →  returns ALL parishioners parish-wide
GET /api/v1/societies/all     →  returns ALL societies parish-wide</pre>
</div>

<h3>How to check permissions in the frontend</h3>
<p>
  After login the user object includes <code>role</code> (name) and <code>role_label</code>. For UI
  decisions (show/hide menu items), use the role name. For fine-grained checks, fetch the group's
  permission list from <code>GET /api/v1/admin/roles</code>.
</p>
<div class="code-block">
  <div class="code-block-header"><span class="lang">tsx</span><button class="copy-btn">copy</button></div>
  <pre><span class="k">const</span> { user } = useAuthStore();

<span class="c">// Coarse: group-based UI visibility</span>
<span class="k">const</span> isGlobalAdmin = user.role === <span class="s">"super_admin"</span>;
<span class="k">const</span> isFinance     = user.role === <span class="s">"church_finance_admin"</span>;

<span class="c">// Show parish-wide stats only for global admins</span>
{isGlobalAdmin &amp;&amp; &lt;ParishWideDashboard /&gt;}

<span class="c">// For scoped users, show only their unit</span>
{!isGlobalAdmin &amp;&amp; user.church_unit_id &amp;&amp; (
  &lt;UnitDashboard unitId={user.church_unit_id} /&gt;
)}</pre>
</div>

<div class="callout tip">
  <p>
    <strong>Tip:</strong> The <code>admin:all</code> permission (super_admin) bypasses every
    <code>require_permission()</code> check on the backend. You only need to configure granular permissions
    for the other groups. Fetch the live list with <code>GET /api/v1/app/groups</code> (public endpoint).
  </p>
</div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<section id="ep-auth">
<h2>Endpoints: Auth</h2>

<h3>Password</h3>
<div class="endpoint"><span class="badge badge-post">POST</span><span class="path">/api/v1/auth/login</span><span class="desc">Password login — form-encoded (<code>username</code> + <code>password</code>)</span></div>
<div class="endpoint"><span class="badge badge-post">POST</span><span class="path">/api/v1/auth/reset-password</span><span class="desc">First-login password reset (<code>temp_password</code> + <code>new_password</code>)</span></div>

<h3>Reference — public app info (<code>/api/v1/app/*</code>)</h3>
<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/app/config</span><span class="desc">App branding — <code>{ name, description, contact_email, contact_phone, website, address, logo_url, support_email }</code>. Single source of truth for UI copy.</span></div>
<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/app/login-config</span><span class="desc">Bootstrap — <code>{ login_methods, groups, church_units }</code>. Single call to drive the entire login UI.</span></div>
<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/app/groups</span><span class="desc">All groups — <code>[{ name, label, description }]</code>. Populate group dropdowns.</span></div>
<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/app/church-units</span><span class="desc">All active church units — <code>[{ id, name, type }]</code>. Populate unit dropdowns.</span></div>

<h3>OTP / Passwordless</h3>
<div class="endpoint"><span class="badge badge-post">POST</span><span class="path">/api/v1/auth/otp/request</span><span class="desc">Request a code — <code>{ identifier }</code> (email or phone). Sends to all enabled channels. Always 202.</span></div>
<div class="endpoint"><span class="badge badge-post">POST</span><span class="path">/api/v1/auth/otp/verify</span><span class="desc">Verify + get token — <code>{ identifier, code }</code></span></div>

<h3>Rendering the login page</h3>
<p>Call <code>GET /api/v1/app/login-config</code> once on app load. Use the response to drive your UI:</p>
<div class="code-block">
  <div class="code-block-header"><span class="lang">tsx</span><button class="copy-btn">copy</button></div>
  <pre><span class="k">const</span> { data } = useLoginConfig(client);
<span class="k">const</span> methods  = data?.data.login_methods;
<span class="k">const</span> groups   = data?.data.groups;       <span class="c">// for group selector dropdown</span>
<span class="k">const</span> units    = data?.data.church_units; <span class="c">// for church unit selector dropdown</span>

<span class="c">// Show the right login form</span>
{methods?.password &amp;&amp; &lt;PasswordLoginForm /&gt;}
{(methods?.otp_email || methods?.otp_sms) &amp;&amp; &lt;OTPLoginForm /&gt;}

<span class="c">// If only OTP is enabled, go straight to passwordless</span>
<span class="k">const</span> otpOnly = !methods?.password &amp;&amp; (methods?.otp_email || methods?.otp_sms);</pre>
</div>
<div class="callout tip">
  <p>All three fields (<code>login_methods</code>, <code>groups</code>, <code>church_units</code>) are configured by an admin via
  <code>PUT /api/v1/admin/settings/auth</code>. No frontend code changes needed when a method is toggled on/off.</p>
</div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<section id="ep-parish">
<h2>Endpoints: Parish</h2>

<h3>Parish</h3>
<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/parish</span><span class="desc">Full parish detail with outstations, schedules, societies, communities</span></div>
<div class="endpoint"><span class="badge badge-put">PUT</span><span class="path">/api/v1/parish</span><span class="desc">Update parish fields (admin:parish)</span></div>

<h3>Outstations</h3>
<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/parish/outstations</span><span class="desc">Paginated list of all outstations</span></div>
<div class="endpoint"><span class="badge badge-post">POST</span><span class="path">/api/v1/parish/outstations</span><span class="desc">Create outstation (admin:outstations)</span></div>
<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/parish/outstations/:id</span><span class="desc">Outstation detail with schedules, societies, communities</span></div>
<div class="endpoint"><span class="badge badge-put">PUT</span><span class="path">/api/v1/parish/outstations/:id</span><span class="desc">Update outstation</span></div>
<div class="endpoint"><span class="badge badge-delete">DELETE</span><span class="path">/api/v1/parish/outstations/:id</span><span class="desc">Delete outstation (admin:outstations)</span></div>

<h3>Mass Schedules</h3>
<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/parish/mass-schedules</span><span class="desc">Parish-level mass schedules</span></div>
<div class="endpoint"><span class="badge badge-post">POST</span><span class="path">/api/v1/parish/mass-schedules</span></div>
<div class="endpoint"><span class="badge badge-put">PUT</span><span class="path">/api/v1/parish/mass-schedules/:id</span></div>
<div class="endpoint"><span class="badge badge-delete">DELETE</span><span class="path">/api/v1/parish/mass-schedules/:id</span></div>
<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/parish/outstations/:id/mass-schedules</span><span class="desc">Outstation schedules</span></div>
<div class="endpoint"><span class="badge badge-post">POST</span><span class="path">/api/v1/parish/outstations/:id/mass-schedules</span></div>
<div class="endpoint"><span class="badge badge-put">PUT</span><span class="path">/api/v1/parish/outstations/:id/mass-schedules/:sid</span></div>
<div class="endpoint"><span class="badge badge-delete">DELETE</span><span class="path">/api/v1/parish/outstations/:id/mass-schedules/:sid</span></div>

<h3>Generic Church Units</h3>
<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/parish/units</span><span class="desc">All units (parish + outstations), paginated</span></div>
<div class="endpoint"><span class="badge badge-post">POST</span><span class="path">/api/v1/parish/units</span></div>
<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/parish/units/:id</span></div>
<div class="endpoint"><span class="badge badge-put">PUT</span><span class="path">/api/v1/parish/units/:id</span></div>
<div class="endpoint"><span class="badge badge-delete">DELETE</span><span class="path">/api/v1/parish/units/:id</span></div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<section id="ep-parishioners">
<h2>Endpoints: Parishioners</h2>

<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/parishioners/all</span><span class="desc">Paginated + filtered list (parishioner:read)</span></div>
<div class="endpoint"><span class="badge badge-post">POST</span><span class="path">/api/v1/parishioners</span><span class="desc">Create (parishioner:write)</span></div>
<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/parishioners/:id</span><span class="desc">Full detail with all sub-resources</span></div>
<div class="endpoint"><span class="badge badge-put">PUT</span><span class="path">/api/v1/parishioners/:id</span><span class="desc">Partial update</span></div>
<div class="endpoint"><span class="badge badge-post">POST</span><span class="path">/api/v1/parishioners/:id/generate-church-id</span></div>
<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/parishioners/:id/occupation</span></div>
<div class="endpoint"><span class="badge badge-post">POST</span><span class="path">/api/v1/parishioners/:id/occupation</span></div>
<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/parishioners/:id/family-info</span></div>
<div class="endpoint"><span class="badge badge-post">POST</span><span class="path">/api/v1/parishioners/:id/family-info</span></div>
<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/parishioners/:id/emergency-contacts</span></div>
<div class="endpoint"><span class="badge badge-post">POST</span><span class="path">/api/v1/parishioners/:id/emergency-contacts</span></div>
<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/parishioners/:id/medical-conditions</span></div>
<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/parishioners/:id/sacraments</span></div>
<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/parishioners/:id/skills</span></div>
<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/parishioners/:id/languages</span></div>
<div class="endpoint"><span class="badge badge-post">POST</span><span class="path">/api/v1/parishioners/import</span><span class="desc">Bulk CSV/Excel import</span></div>
<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/parishioners/verify/:token</span><span class="desc">Email verification link</span></div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<section id="ep-societies">
<h2>Endpoints: Societies</h2>

<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/societies/all</span><span class="desc">Paginated list (society:read). Scoped users see own unit only.</span></div>
<div class="endpoint"><span class="badge badge-post">POST</span><span class="path">/api/v1/societies</span><span class="desc">Create (society:write)</span></div>
<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/societies/:id</span><span class="desc">Detail with leadership</span></div>
<div class="endpoint"><span class="badge badge-put">PUT</span><span class="path">/api/v1/societies/:id</span></div>
<div class="endpoint"><span class="badge badge-delete">DELETE</span><span class="path">/api/v1/societies/:id</span></div>
<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/societies/:id/members</span><span class="desc">Member list with join date and status</span></div>
<div class="endpoint"><span class="badge badge-post">POST</span><span class="path">/api/v1/societies/:id/members</span><span class="desc">Add members <code>{ members: [{parishioner_id, date_joined}] }</code></span></div>
<div class="endpoint"><span class="badge badge-delete">DELETE</span><span class="path">/api/v1/societies/:id/members</span><span class="desc">Remove members <code>{ parishioner_ids: [...] }</code></span></div>
<div class="endpoint"><span class="badge badge-post">POST</span><span class="path">/api/v1/societies/:id/leadership</span></div>
<div class="endpoint"><span class="badge badge-put">PUT</span><span class="path">/api/v1/societies/:id/leadership/:lid</span></div>
<div class="endpoint"><span class="badge badge-delete">DELETE</span><span class="path">/api/v1/societies/:id/leadership/:lid</span></div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<section id="ep-communities">
<h2>Endpoints: Communities</h2>

<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/church-community/all</span><span class="desc">Paginated list. Supports <code>?search=</code></span></div>
<div class="endpoint"><span class="badge badge-post">POST</span><span class="path">/api/v1/church-community</span></div>
<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/church-community/:id</span></div>
<div class="endpoint"><span class="badge badge-put">PUT</span><span class="path">/api/v1/church-community/:id</span></div>
<div class="endpoint"><span class="badge badge-delete">DELETE</span><span class="path">/api/v1/church-community/:id</span></div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<section id="ep-users">
<h2>Endpoints: Users</h2>

<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/user-management</span><span class="desc">List users (admin only)</span></div>
<div class="endpoint"><span class="badge badge-post">POST</span><span class="path">/api/v1/user-management</span></div>
<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/user-management/:id</span></div>
<div class="endpoint"><span class="badge badge-put">PUT</span><span class="path">/api/v1/user-management/:id</span></div>
<div class="endpoint"><span class="badge badge-delete">DELETE</span><span class="path">/api/v1/user-management/:id</span></div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<section id="ep-admin">
<h2>Endpoints: Admin</h2>

<h3>RBAC</h3>
<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/admin/roles</span><span class="desc">List roles with permissions</span></div>
<div class="endpoint"><span class="badge badge-post">POST</span><span class="path">/api/v1/admin/roles</span></div>
<div class="endpoint"><span class="badge badge-put">PUT</span><span class="path">/api/v1/admin/roles/:id</span></div>
<div class="endpoint"><span class="badge badge-delete">DELETE</span><span class="path">/api/v1/admin/roles/:id</span></div>
<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/admin/permissions</span><span class="desc">All available permission codes</span></div>

<h3>Settings</h3>
<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/admin/settings</span><span class="desc">All key-value parish settings (admin:settings)</span></div>
<div class="endpoint"><span class="badge badge-put">PUT</span><span class="path">/api/v1/admin/settings</span><span class="desc">Bulk update: <code>{ settings: { key: value } }</code></span></div>

<h3>App branding configuration</h3>
<p>Requires <code>admin:settings</code> permission. Changes are reflected immediately on the public <code>/auth/app-config</code> endpoint.</p>
<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/admin/settings/app</span><span class="desc">Get current app config — name, description, contact info, logo URL</span></div>
<div class="endpoint"><span class="badge badge-put">PUT</span><span class="path">/api/v1/admin/settings/app</span><span class="desc">Update app config — all fields optional</span></div>

<h3>Auth method configuration</h3>
<p>Requires <code>admin:auth_config</code> permission (super admin only).</p>
<div class="endpoint"><span class="badge badge-get">GET</span><span class="path">/api/v1/admin/settings/auth</span><span class="desc">Get current login method config — password/OTP enabled flags, expiry, code length</span></div>
<div class="endpoint"><span class="badge badge-put">PUT</span><span class="path">/api/v1/admin/settings/auth</span><span class="desc">Update auth config — <code>AuthConfigUpdate</code> body (all fields optional)</span></div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<section id="sdk-setup">
<h2>SDK: Setup</h2>

<p>The SDK lives in <code>sdk/</code> at the backend root. Three files, each with a distinct role:</p>

<div class="table-wrap">
<table>
  <tr><th>File</th><th>What it contains</th><th>How to update</th></tr>
  <tr>
    <td><code>sdk/types.ts</code></td>
    <td>All TypeScript interfaces auto-generated from the OpenAPI schema</td>
    <td><strong>Run <code>make sdk</code></strong> — never edit by hand. Copy the new file to your project.</td>
  </tr>
  <tr>
    <td><code>sdk/client.ts</code></td>
    <td><code>SFOACCClient</code> class — all API call methods</td>
    <td><strong>Copy from backend</strong> when new methods are added (login, OTP, groups, units, etc.).</td>
  </tr>
  <tr>
    <td><code>sdk/hooks.ts</code></td>
    <td>React Query <code>useQuery</code> / <code>useMutation</code> wrappers</td>
    <td><strong>Copy from backend</strong> when new hooks are added. Safe to extend locally for project-specific logic.</td>
  </tr>
</table>
</div>

<div class="callout tip">
  <p><strong>Typical update workflow:</strong> Schema changed → <code>make sdk</code> regenerates <code>types.ts</code>.
  New endpoint added → copy updated <code>client.ts</code> and <code>hooks.ts</code> to your project.</p>
</div>

<p>Copy all three into your React project:</p>

<div class="code-block">
  <div class="code-block-header"><span class="lang">bash</span><button class="copy-btn">copy</button></div>
  <pre>cp sdk/types.ts   src/lib/api/types.ts
cp sdk/client.ts  src/lib/api/client.ts
cp sdk/hooks.ts   src/lib/api/hooks.ts</pre>
</div>

<div class="code-block">
  <div class="code-block-header"><span class="lang">bash — install peer dependency</span><button class="copy-btn">copy</button></div>
  <pre>npm install @tanstack/react-query</pre>
</div>

<p>Create the client instance once and pass it to your hooks (or use React Context):</p>
<div class="code-block">
  <div class="code-block-header"><span class="lang">tsx — src/lib/api/index.ts</span><button class="copy-btn">copy</button></div>
  <pre><span class="k">import</span> { SFOACCClient } <span class="k">from</span> <span class="s">"./client"</span>;

<span class="k">export const</span> api = <span class="k">new</span> SFOACCClient({
  baseUrl: <span class="k">import</span>.meta.env.VITE_API_URL ?? <span class="s">"http://localhost:8000"</span>,
});

<span class="c">// After login:</span>
<span class="c">// api.setToken(loginResponse.access_token);</span>
<span class="c">// localStorage.setItem("token", loginResponse.access_token);</span></pre>
</div>

<p>Restore the token on app startup:</p>
<div class="code-block">
  <div class="code-block-header"><span class="lang">tsx — src/main.tsx</span><button class="copy-btn">copy</button></div>
  <pre><span class="k">import</span> { QueryClient, QueryClientProvider } <span class="k">from</span> <span class="s">"@tanstack/react-query"</span>;
<span class="k">import</span> { api } <span class="k">from</span> <span class="s">"./lib/api"</span>;

<span class="c">// Restore saved token</span>
<span class="k">const</span> saved = localStorage.getItem(<span class="s">"token"</span>);
<span class="k">if</span> (saved) api.setToken(saved);

<span class="k">const</span> queryClient = <span class="k">new</span> QueryClient();

ReactDOM.createRoot(document.getElementById(<span class="s">"root"</span>)!).render(
  &lt;QueryClientProvider client={queryClient}&gt;
    &lt;App /&gt;
  &lt;/QueryClientProvider&gt;
);</pre>
</div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<section id="sdk-client">
<h2>SDK: Client methods</h2>

<div class="table-wrap">
<table>
  <tr><th>Method</th><th>Returns</th></tr>
  <tr><td><code>getAppConfig()</code></td><td><code>{ data: { name, description, contact_email, … } }</code> — public, app branding config</td></tr>
  <tr><td><code>getLoginConfig()</code></td><td><code>{ data: { login_methods, groups, church_units } }</code> — public, single bootstrap call for login UI</td></tr>
  <tr><td><code>listGroups()</code></td><td><code>{ data: [{name, label, description}][] }</code> — public, no token needed</td></tr>
  <tr><td><code>listChurchUnitsPublic()</code></td><td><code>{ data: [{id, name, type}][] }</code> — public, no token needed</td></tr>
  <tr><td><code>login(email, password)</code></td><td><code>LoginResponse</code></td></tr>
  <tr><td><code>requestOtp(identifier)</code></td><td><code>APIResponse</code> — always 202. Sends to all enabled channels.</td></tr>
  <tr><td><code>verifyOtp(identifier, code)</code></td><td><code>LoginResponse</code></td></tr>
  <tr><td><code>getParish()</code></td><td><code>APIResponse&lt;ParishDetail&gt;</code></td></tr>
  <tr><td><code>listOutstations(params?)</code></td><td><code>PagedResponse&lt;ChurchUnit&gt;</code></td></tr>
  <tr><td><code>getOutstation(id)</code></td><td><code>APIResponse&lt;OutstationDetail&gt;</code></td></tr>
  <tr><td><code>listParishioners(filters?)</code></td><td><code>PagedResponse&lt;Parishioner&gt;</code></td></tr>
  <tr><td><code>getParishioner(id)</code></td><td><code>APIResponse&lt;ParishionerDetailed&gt;</code></td></tr>
  <tr><td><code>listSocieties(params?)</code></td><td><code>PagedResponse&lt;Society&gt;</code></td></tr>
  <tr><td><code>listCommunities(params?)</code></td><td><code>PagedResponse&lt;ChurchCommunity&gt;</code></td></tr>
  <tr><td><code>listUsers(params?)</code></td><td><code>APIResponse&lt;PagedData&lt;User&gt;&gt;</code></td></tr>
  <tr><td><code>createParishioner(data)</code></td><td><code>APIResponse&lt;Parishioner&gt;</code></td></tr>
  <tr><td><code>updateParishioner(id, data)</code></td><td><code>APIResponse&lt;Parishioner&gt;</code></td></tr>
</table>
</div>

<div class="callout">
  <p>All methods throw <code>APIError</code> (with <code>.status</code> and <code>.message</code>) on non-2xx responses.</p>
</div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<section id="sdk-hooks">
<h2>SDK: React Query Hooks</h2>

<div class="table-wrap">
<table>
  <tr><th>Hook</th><th>Notes</th></tr>
  <tr><td><code>useAppConfig(client)</code></td><td>App name, description, contact info. Public, no token. <code>staleTime: Infinity</code></td></tr>
  <tr><td><code>useLoginConfig(client)</code></td><td>Bootstrap — login methods + groups + church units. Public, no token. <code>staleTime: Infinity</code></td></tr>
  <tr><td><code>useGroups(client)</code></td><td>All groups — public, no token. <code>staleTime: Infinity</code></td></tr>
  <tr><td><code>useChurchUnitsPublic(client)</code></td><td>All active units — public, no token. <code>staleTime: Infinity</code></td></tr>
  <tr><td><code>useParish(client)</code></td><td>Full parish detail</td></tr>
  <tr><td><code>useOutstations(client, params?)</code></td><td>Paginated outstations</td></tr>
  <tr><td><code>useOutstation(client, id)</code></td><td>Single outstation detail</td></tr>
  <tr><td><code>useParishioners(client, filters?)</code></td><td>Paginated + filtered</td></tr>
  <tr><td><code>useParishioner(client, id)</code></td><td>Full detail</td></tr>
  <tr><td><code>useSocieties(client, params?)</code></td><td></td></tr>
  <tr><td><code>useSociety(client, id)</code></td><td></td></tr>
  <tr><td><code>useCommunities(client, params?)</code></td><td></td></tr>
  <tr><td><code>useParishSchedules(client)</code></td><td></td></tr>
  <tr><td><code>useOutstationSchedules(client, id)</code></td><td></td></tr>
  <tr><td><code>useUsers(client, params?)</code></td><td></td></tr>
  <tr><td><code>useCreateParishioner(client)</code></td><td>Mutation — invalidates <code>parishioners</code></td></tr>
  <tr><td><code>useUpdateParishioner(client)</code></td><td>Mutation</td></tr>
  <tr><td><code>useCreateSociety(client)</code></td><td>Mutation</td></tr>
  <tr><td><code>useUpdateOutstation(client)</code></td><td>Mutation</td></tr>
  <tr><td><code>useUpdateParish(client)</code></td><td>Mutation</td></tr>
</table>
</div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<section id="sdk-examples">
<h2>SDK: Examples</h2>

<h3>Login page</h3>
<div class="code-block">
  <div class="code-block-header"><span class="lang">tsx</span><button class="copy-btn">copy</button></div>
  <pre><span class="k">import</span> { api } <span class="k">from</span> <span class="s">"@/lib/api"</span>;

<span class="k">async function</span> handleLogin(email: <span class="t">string</span>, password: <span class="t">string</span>) {
  <span class="k">try</span> {
    <span class="k">const</span> res = <span class="k">await</span> api.login(email, password);
    localStorage.setItem(<span class="s">"token"</span>, res.access_token);
    <span class="c">// token auto-stored in client by login()</span>
    navigate(<span class="s">"/dashboard"</span>);
  } <span class="k">catch</span> (err: <span class="k">any</span>) {
    setError(err.message);  <span class="c">// "Invalid credentials"</span>
  }
}</pre>
</div>

<h3>Parishioner directory with filters</h3>
<div class="code-block">
  <div class="code-block-header"><span class="lang">tsx</span><button class="copy-btn">copy</button></div>
  <pre><span class="k">import</span> { useParishioners } <span class="k">from</span> <span class="s">"@/lib/api/hooks"</span>;
<span class="k">import</span> { api } <span class="k">from</span> <span class="s">"@/lib/api"</span>;

<span class="k">export function</span> ParishionerList() {
  <span class="k">const</span> [page, setPage] = useState(<span class="v">0</span>);
  <span class="k">const</span> [search, setSearch] = useState(<span class="s">""</span>);

  <span class="k">const</span> { data, isLoading } = useParishioners(api, {
    skip:   page * <span class="v">20</span>,
    limit:  <span class="v">20</span>,
    search: search || <span class="k">undefined</span>,
    membership_status: <span class="s">"active"</span>,
  });

  <span class="k">if</span> (isLoading) <span class="k">return</span> &lt;Spinner /&gt;;

  <span class="k">return</span> (
    &lt;&gt;
      &lt;p&gt;{data?.total} parishioners&lt;/p&gt;
      {data?.items.map(p =&gt; &lt;ParishionerRow key={p.id} p={p} /&gt;)}
      &lt;Pagination
        page={page}
        total={Math.ceil((data?.total ?? <span class="v">0</span>) / <span class="v">20</span>)}
        onChange={setPage}
      /&gt;
    &lt;/&gt;
  );
}</pre>
</div>

<h3>Parish homepage widget</h3>
<div class="code-block">
  <div class="code-block-header"><span class="lang">tsx</span><button class="copy-btn">copy</button></div>
  <pre><span class="k">import</span> { useParish } <span class="k">from</span> <span class="s">"@/lib/api/hooks"</span>;

<span class="k">export function</span> ParishCard() {
  <span class="k">const</span> { data: parish } = useParish(api);

  <span class="k">return</span> (
    &lt;div&gt;
      &lt;h1&gt;{parish?.name}&lt;/h1&gt;
      &lt;p&gt;{parish?.address}&lt;/p&gt;

      &lt;h2&gt;Mass Schedule&lt;/h2&gt;
      {parish?.mass_schedules.map(s =&gt; (
        &lt;div key={s.id}&gt;{s.day_of_week} {s.time} — {s.language}&lt;/div&gt;
      ))}

      &lt;h2&gt;Outstations&lt;/h2&gt;
      {parish?.outstations.map(o =&gt; (
        &lt;div key={o.id}&gt;{o.name}&lt;/div&gt;
      ))}
    &lt;/div&gt;
  );
}</pre>
</div>

<h3>Keep SDK types in sync</h3>
<div class="code-block">
  <div class="code-block-header"><span class="lang">bash</span><button class="copy-btn">copy</button></div>
  <pre><span class="c"># Regenerate sdk/types.ts whenever schemas change:</span>
make sdk</pre>
</div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<section id="enums">
<h2>Enums &amp; Constants</h2>

<div class="table-wrap">
<table>
  <tr><th>Enum</th><th>Values</th></tr>
  <tr><td><code>ChurchUnitType</code></td><td><code>PARISH</code> · <code>OUTSTATION</code></td></tr>
  <tr><td><code>DayOfWeek</code></td><td><code>SUNDAY</code> · <code>MONDAY</code> … <code>SATURDAY</code></td></tr>
  <tr><td><code>MassType</code></td><td><code>SUNDAY</code> · <code>WEEKDAY</code> · <code>VIGIL</code> · <code>SPECIAL</code></td></tr>
  <tr><td><code>MeetingFrequency</code></td><td><code>weekly</code> · <code>biweekly</code> · <code>monthly</code> · <code>quarterly</code> · <code>annually</code></td></tr>
  <tr><td><code>LeadershipRole</code></td><td><code>president</code> · <code>vice_president</code> · <code>secretary</code> · <code>treasurer</code> · <code>welfare</code> · <code>other</code></td></tr>
  <tr><td><code>Gender</code></td><td><code>male</code> · <code>female</code> · <code>other</code></td></tr>
  <tr><td><code>MaritalStatus</code></td><td><code>single</code> · <code>married</code> · <code>widowed</code> · <code>divorced</code> · <code>separated</code></td></tr>
  <tr><td><code>MembershipStatus</code></td><td><code>active</code> · <code>deceased</code> · <code>disabled</code></td></tr>
  <tr><td><code>VerificationStatus</code></td><td><code>unverified</code> · <code>verified</code> · <code>pending</code></td></tr>
  <tr><td><code>UserStatus</code></td><td><code>active</code> · <code>inactive</code> · <code>reset_required</code></td></tr>
  <tr><td><code>LifeStatus</code></td><td><code>alive</code> · <code>deceased</code></td></tr>
  <tr><td><code>SacramentType</code></td><td><code>baptism</code> · <code>confirmation</code> · <code>eucharist</code> · <code>reconciliation</code> · <code>anointing</code> · <code>holy_orders</code> · <code>matrimony</code></td></tr>
</table>
</div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<section id="permissions">
<h2>Permissions</h2>
<p>
  Permission codes are attached to Roles. The current user's permissions are available from the
  <code>User.role</code> name — you can fetch the full role list from <code>GET /api/v1/admin/permissions</code>.
</p>

<div class="table-wrap">
<table>
  <tr><th>Code</th><th>Module</th><th>Description</th></tr>
  <tr><td><code>admin:all</code></td><td>admin</td><td>Full system access — bypasses all permission checks</td></tr>
  <tr><td><code>admin:parish</code></td><td>admin</td><td>Manage parish info and all units</td></tr>
  <tr><td><code>admin:outstations</code></td><td>admin</td><td>Create/delete outstations across the parish</td></tr>
  <tr><td><code>admin:outstation</code></td><td>admin</td><td>Manage own assigned church unit only</td></tr>
  <tr><td><code>admin:settings</code></td><td>admin</td><td>Read/write all parish settings</td></tr>
  <tr><td><code>admin:roles</code></td><td>admin</td><td>Create/edit RBAC roles and assign permissions</td></tr>
  <tr><td><code>admin:auth_config</code></td><td>admin</td><td>Configure login methods (password/OTP on/off, expiry)</td></tr>
  <tr><td><code>parishioner:read</code></td><td>parishioners</td><td>List and view parishioner records</td></tr>
  <tr><td><code>parishioner:write</code></td><td>parishioners</td><td>Create and update parishioners</td></tr>
  <tr><td><code>parishioner:delete</code></td><td>parishioners</td><td>Delete parishioner records</td></tr>
  <tr><td><code>parishioner:import</code></td><td>parishioners</td><td>Bulk import via CSV/Excel</td></tr>
  <tr><td><code>parishioner:generate_id</code></td><td>parishioners</td><td>Generate church IDs</td></tr>
  <tr><td><code>parishioner:verify</code></td><td>parishioners</td><td>Mark parishioner records as verified</td></tr>
  <tr><td><code>society:read</code></td><td>societies</td><td>View societies and membership</td></tr>
  <tr><td><code>society:write</code></td><td>societies</td><td>Create and manage societies</td></tr>
  <tr><td><code>society:membership</code></td><td>societies</td><td>Add/remove society members and leadership</td></tr>
  <tr><td><code>user:read</code></td><td>users</td><td>List and view user accounts</td></tr>
  <tr><td><code>user:write</code></td><td>users</td><td>Create and update user accounts</td></tr>
  <tr><td><code>user:delete</code></td><td>users</td><td>Delete user accounts</td></tr>
  <tr><td><code>statistics:read</code></td><td>statistics</td><td>View parish statistics and dashboards</td></tr>
  <tr><td><code>reporting:read</code></td><td>reporting</td><td>View reports and data exports</td></tr>
  <tr><td><code>messaging:send</code></td><td>messaging</td><td>Send bulk SMS/email messages</td></tr>
  <tr><td><code>finance:read</code></td><td>finance</td><td>View financial records</td></tr>
  <tr><td><code>finance:write</code></td><td>finance</td><td>Create and manage financial records</td></tr>
</table>
</div>

<div class="callout tip">
  <p>Fetch the live permission list from <code>GET /api/v1/admin/permissions</code>. Roles and their
  assigned permissions are at <code>GET /api/v1/admin/roles</code>.</p>
</div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<section id="swagger">
<h2>Swagger / OpenAPI</h2>
<p>
  Interactive API explorer and machine-readable schema are available at:
</p>
<ul>
  <li><strong>Swagger UI</strong> — <a href="/api/v1/docs" style="color:var(--accent)">/api/v1/docs</a></li>
  <li><strong>ReDoc</strong> — <a href="/api/v1/redoc" style="color:var(--accent)">/api/v1/redoc</a></li>
  <li><strong>OpenAPI JSON</strong> — <a href="/api/v1/openapi.json" style="color:var(--accent)">/api/v1/openapi.json</a></li>
</ul>
<div class="callout tip">
  <p>Use <code>make sdk</code> to regenerate <code>sdk/types.ts</code> from the live OpenAPI schema after any schema changes.</p>
</div>
</section>

</main>

<script>
// ── Copy buttons ──────────────────────────────────────────────────────────────
document.querySelectorAll(".copy-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    const pre = btn.closest(".code-block").querySelector("pre");
    navigator.clipboard.writeText(pre.innerText).then(() => {
      const orig = btn.textContent;
      btn.textContent = "copied!";
      setTimeout(() => btn.textContent = orig, 1500);
    });
  });
});

// ── Active nav link on scroll ─────────────────────────────────────────────────
const sections = document.querySelectorAll("section[id]");
const navLinks  = document.querySelectorAll("nav#sidebar a");
const observer  = new IntersectionObserver(entries => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      navLinks.forEach(a => a.classList.remove("active"));
      const active = document.querySelector(`nav#sidebar a[href="#${e.target.id}"]`);
      if (active) active.classList.add("active");
    }
  });
}, { threshold: 0.25 });
sections.forEach(s => observer.observe(s));
</script>
</body>
</html>"""


@router.get("/guide", response_class=HTMLResponse, include_in_schema=False)
async def frontend_guide():
    """Frontend integration guide — developer documentation page."""
    return HTMLResponse(content=_HTML)

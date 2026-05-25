# AI Development Compliance Readiness

**A 4–6 week engagement that turns your AI-assisted development practice
into something your auditor will accept and your CISO can sign off on.**

> ⚠️ **Internal note — read before using client-facing.**
> This is a v1 draft to anchor the offer shape. Three things to validate
> *before* sending to a prospect:
> 1. The control mappings in "What you get" are *illustrative placeholders*
>    based on framework summaries, not certified mappings. Validate each
>    one against the actual control text during your domain-learning
>    phase (months 1–2) or pay a fractional GRC consultant ~$500–1k for
>    a single review pass. Sending unvalidated mappings to a real
>    compliance officer is reputational suicide.
> 2. The pricing assumes you have at least one design-partner reference
>    by the time you quote full price. Until then, lead with a discounted
>    design-partner offer (~$8–12k) and earn the case study first.
> 3. You need E&O insurance ($1–2M cover, ~$2–4k/yr) and ideally a real
>    company entity (LLC / Ltd) before pitching at this ACV. Enterprise
>    procurement will ask, and "sole trader" closes doors.
> Strip this banner before sending the doc anywhere.

---

## The regulatory pressure your team is already feeling

In the last 18 months, the audit questions have changed:

- **EU AI Act** (high-risk obligations begin 2026): Articles 9, 12, and 14
  require documented risk management, traceable logs, and human oversight
  records for AI used in high-risk contexts — which includes most regulated
  software development workflows. Penalties reach €35M or 7% of global
  revenue.
- **NIST AI RMF + ISO/IEC 42001**: increasingly cited in vendor security
  questionnaires from your enterprise customers. "Do you use generative AI
  in your SDLC, and how is it controlled?" is the new "do you have a WAF."
- **SOC 2 auditors** are starting to ask: *"Walk me through your controls
  around AI-assisted code generation."* Most engineering teams have no
  structured answer beyond a Notion page that says "engineers must review
  AI-generated code."

Your codebase is being touched by Claude / Copilot / Cursor every day. You
have no signed record of which sessions ran, what they changed, who
reviewed them, or whether your invariants held. When the auditor — or
worse, the regulator — asks, you will not have an answer.

This engagement gives you the answer.

---

## Who this is for

Regulated mid-market firms, typically 200–1,500 employees, where:

- You're already pursuing or maintaining **SOC 2 Type II, ISO 27001, HIPAA,
  PCI-DSS, FedRAMP, or EU AI Act conformity** — or planning to within 12 months
- Engineering already uses **Claude Code, Cursor, Copilot, or similar** in
  production codebases
- A specific person owns AI governance: **Head of Engineering, Director of
  Compliance, fractional CISO, or VP of Security**
- You've had at least one customer or auditor ask about your AI controls
  and the answer made you uncomfortable

**Not for:** firms not yet adopting AI dev tooling (premature), pre-Seed
startups (no compliance pressure yet), or organizations looking for a
SOC 2 audit firm (we're complementary to your auditor, not a replacement).

---

## What you get

A documented, deployable, audit-acceptable AI-development control framework
mapped to the specific frameworks under which your firm operates.

### Tier 1 — Foundation ($18,000)

| Deliverable | What it actually is |
|---|---|
| **Harness deployment (1 repo)** | The Claude Harness installed and configured on a single primary repository with audit-grade retention settings, signed session logs, and per-commit invariant verification |
| **Single-framework control mapping** | Choose one: SOC 2, ISO 27001, NIST AI RMF, or ISO 42001. Each harness artifact (sessions, tickets, invariants, Opus reviews) mapped to specific controls/subcategories with citations |
| **AI use policy draft** | A written policy your General Counsel can review and your CISO can adopt, covering authorized AI tools, review requirements, prohibited use, and incident response |
| **Evidence-pack template** | Templates your team uses each quarter to produce evidence artifacts for auditors: AI session summary report, invariant compliance report, controlled-change log |
| **Team training (90 min)** | One live session with engineering + compliance stakeholders covering the workflow, the controls it satisfies, and how to produce the evidence pack |
| **30-day async support** | Slack/email channel for hook tuning, evidence-pack questions, and edge cases as your team beds it in |

### Tier 2 — Standard ($24,000)

Everything in Foundation, plus:

| Additional deliverable | What it actually is |
|---|---|
| **Up to 3 repositories** | Deployment across your top 3 AI-touched repos (typical: main product, internal tooling, infra-as-code) |
| **Multi-framework mapping** | Up to 2 frameworks mapped (e.g., SOC 2 + NIST AI RMF, or ISO 27001 + EU AI Act) with explicit traceability matrix |
| **Auditor pre-walkthrough call** | One 60-min call between me and your auditor or fractional CISO to validate the evidence approach *before* you commit to it internally |
| **60-day async support** | Extended channel |

### Tier 3 — Extended ($32,000)

Everything in Standard, plus:

| Additional deliverable | What it actually is |
|---|---|
| **Up to 5 repos OR full monorepo** | Broader deployment |
| **Three-framework coverage** | Add EU AI Act Article 9/12/14 conformity mapping where applicable |
| **Sample-data evidence pack** | I produce one real quarterly evidence pack from your live data, so your team has a complete worked example to follow |
| **6-month follow-up review** | A half-day review at the 6-month mark to validate the controls are still operating, surface drift, and tune for any new framework requirements |
| **90-day async support** | Full support window |

---

## Illustrative control mappings (validate before client use — see internal note)

These are the *kind* of mappings you walk an auditor through. Specific
control IDs vary by framework version and must be validated:

| Harness artifact | Maps to |
|---|---|
| Signed session log (per-session timestamp, model used, commit hash) | SOC 2 CC7.1 (system monitoring), CC8.1 (change management); NIST AI RMF MEASURE-2.3 (AI system performance monitoring) |
| Architecture invariant enforcement at every session close | SOC 2 CC8.1 (change management controls); ISO 27001 A.8.32 (change management); EU AI Act Art. 9 (risk management) |
| Ticket-level acceptance criteria with closure attribution | SOC 2 CC8.1; ISO 42001 8.2 (AI system requirements); NIST AI RMF MANAGE-1.3 |
| Opus post-session review (independent second-opinion artifact) | NIST AI RMF MEASURE-3.1 (effectiveness measurement); ISO 42001 9.1 (monitoring and measurement) |
| Commit-msg hook validation + structured commit conventions | SOC 2 CC8.1 (change management evidence); ISO 27001 A.8.32 |
| Static-analysis hooks on AI-touched paths | SOC 2 CC7.1; NIST AI RMF MEASURE-2.7 |
| Workspace isolation enforcement | SOC 2 CC6.1 (logical access); ISO 27001 A.8.3 |

A complete traceability matrix specific to your chosen framework(s) is
produced as part of the engagement.

---

## What this is *not*

Clear scope boundaries — I will not let these blur in scoping calls:

- **Not a SOC 2 / ISO 27001 / HIPAA audit.** I do not issue attestation
  letters or certifications. Your existing audit firm does that; this
  engagement gives you the evidence they need to do their job.
- **Not legal advice.** I am not your General Counsel. The AI use policy
  is a starting draft your legal team adapts.
- **Not a managed service.** I install the controls, train your team,
  and step out. Optional ongoing review is available as a separate
  retainer; not pushed.
- **Not a code review or security pentest** of your application code.
  The engagement is about *controls around AI-assisted development*, not
  the security of your application itself.
- **Not for non-regulated firms.** If you don't have a compliance driver,
  the $1,200 productized harness setup is a better fit.

---

## Timeline & structure (4–6 weeks)

| Week | What happens | Your team's time |
|---|---|---|
| **Week 0 — Discovery (free)** | 45-min call: confirm framework scope, repo count, stakeholder alignment, tier selection | 1 person, 45 min |
| **Week 1 — Kickoff** | 90-min call with engineering lead + compliance lead. Walk current state: AI tooling, repos, existing policy, audit history. Confirm framework scope and tier | 2 people, 90 min |
| **Week 2 — Async assessment + draft policy** | I draft the AI use policy and the control mapping doc based on Week 1. You review async | 1 person, ~2hr review |
| **Week 3 — Harness deployment** | I deploy the harness with audit-grade settings on the chosen repos. PR opened against each repo for engineering review | 1 engineer, ~3hr review |
| **Week 4 — Evidence-pack templates** | I produce the evidence-pack templates and (Tier 3) one populated sample. You review | 2 people, ~3hr review |
| **Week 5 — Training + handoff** | 90-min training with engineering + compliance. Walkthrough of: deployed harness, control mapping, policy, evidence-pack production | 5–10 people, 90 min |
| **Week 5–6 — Auditor pre-walkthrough** (Tier 2+) | 60-min call with your auditor/CISO to validate approach | 1–2 people, 60 min |
| **Weeks 6–18 — Async support** | Slack channel for questions, hook tuning, evidence-pack edge cases | As needed |

Total client-side time investment: ~10–15 hours of meetings + ~10 hours
of async review work spread over 6 weeks.

---

## Pricing & terms

- **Tier 1:** $18,000 — 50% on signing, 50% on training completion
- **Tier 2:** $24,000 — 50% on signing, 50% on training completion
- **Tier 3:** $32,000 — 40% on signing, 30% at Week 4, 30% on training completion
- Standard MSA + SOW; can accept your paper or provide mine
- Standard NDA and DPA available; BAA available for HIPAA-context work
- E&O insurance: $1M coverage, evidence on request
- Refund guarantee: if Week 1 reveals the engagement is not a fit, full
  refund of payment-1 less $1,500 discovery cost. No hard feelings.

---

## Engagement security posture

- **Source code access:** read-only to specified repos via deploy key or
  GitHub App, scoped to engagement duration. Revoked at handoff.
- **Data handling:** no production data, customer PII, or secrets are
  required for the engagement. Harness installation operates on source
  code structure, not data.
- **AI tooling used during delivery:** Claude API (Anthropic), under
  Anthropic's data-processing terms. No client code is sent to public
  training data sources.
- **Subprocessors:** none. Solo delivery by named principal.
- **Deliverable storage:** all deliverables produced in your repos. No
  vendor-side data retention beyond engagement notes.

---

## FAQ

**Q: Are you SOC 2 certified yourselves?**
No. I am a solo specialist consultant; SOC 2 certification applies to
SaaS/processor entities. I carry E&O insurance and operate under standard
NDA + DPA. If you require SOC 2'd vendors only, I am not your fit — but
that requirement typically applies to processors handling your data, not
to professional services engagements that operate on your source code
under your access controls.

**Q: What happens if our auditor doesn't accept the evidence pack?**
Tier 2+ includes a pre-validation call with your auditor specifically to
prevent this. If — despite that — your auditor finds the evidence
inadequate, I will revise the controls and evidence templates at no
charge for up to 30 days post-engagement. This has not occurred to date.
[*Internal: be honest about your track record once you have one. Don't
fabricate.*]

**Q: How does this compare to Vanta / Drata / Secureframe?**
Complementary. Those platforms collect *general* SOC 2 evidence; none of
them have specific controls for AI-assisted development workflows. The
artifacts this engagement produces feed *into* your Vanta/Drata
instance as custom evidence.

**Q: Will the harness keep working after you leave?**
Yes. It lives in your repos, runs on your infrastructure, and your team
owns it. The hooks, scripts, and configuration are all in-tree. There is
no vendor lock-in and no recurring license.

**Q: What if our framework requirements change mid-engagement?**
Small additions handled in-scope. Adding a new framework mid-engagement
is a change order: +$4,000 per additional framework.

**Q: Can you also help us pass the actual SOC 2 audit?**
No — that's your audit firm's job. I prepare the AI-controls portion;
they conduct the full audit. I work alongside several audit firms and
can refer if you don't yet have one engaged.

**Q: Do you handle EU AI Act compliance specifically?**
Articles 9 (risk management), 12 (logging), and 14 (human oversight) map
cleanly to the harness's session/invariant/review artifacts. Articles
involving model-card disclosures, conformity assessment, and notified
body interaction are *outside scope* — those are the responsibility of
the AI provider (Anthropic, OpenAI), not deployers, in most cases.

**Q: What stacks have you done this for?**
[*Internal: fill in honestly as you accumulate engagements. Until then:
"The harness is stack-agnostic — Python, TypeScript, Go, Java, Rust
codebases have all been deployed. Your specific stack is confirmed in
the Week 0 discovery call as a fit-check."*]

**Q: How long until we see audit-ready evidence?**
The evidence-pack templates are deliverable by end of Week 4. Your first
*populated* quarterly evidence pack is produced 90 days after deployment,
once the harness has run through a full quarter of real sessions.

---

## Next step

Book a 45-minute discovery call: [Calendly link]

Or email a one-paragraph summary of: (1) which framework(s) you're under,
(2) approximate repo count and AI tooling in use, (3) the audit or
compliance deadline driving the timeline → martin.p2907@hotmail.com

A response within 1 business day; discovery call within 5 business days.

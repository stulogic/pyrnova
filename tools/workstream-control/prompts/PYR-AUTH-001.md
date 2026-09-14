## Task: Authentication, MFA & Identity Roadmap

Define an appropriate authentication and identity architecture for Pyrnova — right-sized for Phase 1, with a credible path to enterprise — without importing unnecessary enterprise complexity now.

Do this:

1. **Phase 1 baseline.** Recommend the minimum credible auth for launch: login model, password/credential handling, MFA approach, session management, account recovery, and admin/privileged access. Favour proven, standard mechanisms and well-supported libraries/providers over bespoke crypto. State concrete choices, not options.

2. **Threat & trust fit.** Justify choices against Pyrnova's buyers and data sensitivity (defense and security-conscious commercial). Note where the bar is higher than a typical SaaS and what that changes.

3. **Enterprise path.** Lay out the later-phase roadmap: SSO (SAML/OIDC), SCIM provisioning, org/tenant and role models, audit logging, and any compliance-driven controls. Sequence them and state which are triggered by which customer demand — do not pull them into Phase 1 unless justified.

4. **Build vs buy.** Recommend, using current web research, whether to use an identity provider/service or build in-house for each stage, with trade-offs and rough cost/lock-in implications.

5. **Decisions & risks.** List the concrete decisions to lock for Phase 1 and the key risks/unknowns.

Keep Phase 1 lean and defensible; keep the enterprise path clear but deferred. Cite sources for provider capabilities and standards.

# V2.18 — Cloudflare Web Analytics

The supplied Cloudflare Web Analytics module script is included once before `</body>` in `dist/index.html`, using the user's public site token. It loads from `https://static.cloudflareinsights.com/beacon.min.js`; no Cloudflare API secret or server credential is required.

After merge, deploy latest main on Render and hard-refresh/open the website. Then check Cloudflare → Web Analytics → this site. Analytics begins after deployment; old visits are not reconstructed. Browser blockers can prevent collection. The owner’s visits are included: owner exclusion, custom Run collections events, notifications and tagged Accenture-link tracking are not implemented. Country/activity metrics do not prove who visited.

No DNS/hosting move, SQL, package or environment change. Backend version metadata only: app v2.18 / UI workflow-19. Existing Incognito/session behavior, email/model quotas, invoice workflows and the guide screenshot remain unchanged. Start fresh demo remains cancelled.

Validation: parsed final HTML to verify exactly one beacon with the supplied token/source/module type, all five existing app scripts and no fresh-demo feature. Python compilation passed. No external beacon execution, Cloudflare account changes, live model/email calls or deployment performed. Live dashboard verification is the user's post-deploy check.

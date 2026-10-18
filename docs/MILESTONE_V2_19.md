# V2.19 — GitHub source link and credential review

The header now has **View source on GitHub** beside How it works. It opens the canonical repository in a new tab. GitHub enforces repository access; the website does not grant access or change visibility.

A private repository is visible only to authorized GitHub users. Invite individual interviewers to keep it private, or make it public for unrestricted source access. The live demo itself remains accessible independently. Repository visibility was not changed by this milestone.

## Credential review — 2026-10-18

Reviewed main at `d03f1f64c5be2fe2804498d800fa24b6cb1bb41d` and all 30 branch heads available at review time, including the abandoned fresh-demo branch solely for auditing. Their reachable history contained 69 commits, 41 distinct complete trees and 473 distinct file blobs. No tag refs were returned by GitHub's matching-refs endpoint.

All 471 text blob versions and commit messages were scanned for common Groq, Resend, Supabase, OpenAI, GitHub, AWS, webhook, JWT, private-key, credential-URL and literal secret-assignment patterns. Matches were reviewed in context: test-only session/owner secrets and the webhook verification test vector. No apparent live credentials were identified. The only tracked environment file across those trees was `.env.example`, with blank credential fields. `.gitignore` excludes actual environment files.

The two binary assets were a favicon and the previously inspected demo inbox screenshot. They were excluded from text scanning; no binary metadata/forensic audit was performed. The screenshot contains email subject lines; review its presentation before making the repository public.

This is a point-in-time pattern review, not a guarantee that no secret exists. It does not cover deleted/unreachable Git objects, issues/PR discussions, Actions logs/artifacts, service dashboards or runtime environment values. It does not verify that credentials previously shared in chat were revoked. Rotate any such credentials in their service dashboards; keep replacement values only in server environment settings or ignored local `.env`. Do not use test fixtures as deployment secrets.

## Hands-on check

1. Merge this PR, pull latest main if working locally, deploy and hard-refresh the website.
2. Click View source on GitHub. In a signed-out browser, a private repository will remain inaccessible; invited collaborators must sign in.
3. Choose public visibility only when you are comfortable sharing the source, history and screenshot. Otherwise invite the interviewer's GitHub account.

No SQL, package or environment changes are needed. App v2.19 / UI workflow-20 identify this build. Existing workflows and Incognito behavior remain; Start fresh demo stays cancelled.

Validation: all 120 current tracked files matched the reviewed GitHub tree before edits. HTML checks verified the exact repository URL, accessible new-tab label, safe link relation, preserved How it works control, five existing app scripts and one analytics beacon. Python compilation passed. No live model/email calls, repository visibility change or deployment performed.

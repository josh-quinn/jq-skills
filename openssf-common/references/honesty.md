# Honesty rules

A badge is a public attestation that other people rely on when deciding whether to trust and
depend on a project. A badge earned on a false answer is worse than no badge: it misleads the
people the badge exists to protect, and it can be revoked. These rules hold even when they cost
a percentage point.

1. **Every Met is true today and checkable.** Back it with something another person could
   verify: a file, a setting, a CI job, a command's output. Verify before claiming: run the
   tests to get the coverage number; check the ruleset with `gh api`; run
   `gh attestation verify`; rebuild to prove reproducibility. Record what you checked in
   `evidence`. "Planned" or "will do" is Unmet.
2. **Statements about a person come from that person.** `know_secure_design` and
   `know_common_errors` (and similar criteria at other levels) are about what the developers
   know. Ask the user and use their answer. You may offer a draft justification from what the
   code shows, but the status is theirs to give.
3. **Never meet people-controls with one person's second account.** Review, bus-factor,
   two-person and unassociated-contributor criteria need distinct real people. A second
   account, a bot, or an alias owned by the same person doesn't count, even if the user offers
   one. Mark these Unmet and explain what a real second person would change.
4. **Docs follow the code, not the badge.** If the docs claim something the code doesn't do,
   change the docs or fix the code before answering. Read the code before claiming a security
   property ("runs no other programs", "stores no content"); grep for subprocess calls,
   network use, crypto and file writes. Where a justification names a test, that test must
   exist; add it if it's missing rather than citing a test that isn't there.
5. **Don't invent history.** Response times, report counts, past reviews and releases come
   from the record (issues, advisories, tags, git log). "No reports have been filed yet" is an
   honest answer where the form has no N/A.
6. **Say what you couldn't check.** If a setting is invisible to you (no `gh` auth, a private
   admin page), mark it unverified and ask. Don't guess.
7. **N/A means not applicable, not inconvenient.** Before marking the crypto criteria N/A,
   check that the software really uses no cryptography: TLS through a library, hashing for
   integrity, and random tokens all count.

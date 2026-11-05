# journal/

Dated documents: plans, handoffs, incident reports, designs, reviews. One place for
everything that tells a moment, so the question "where does it go?" does not arise.

- Name: `YYYY-MM-DD-<genre>-<slug>.md`, where the date is the date of the fact and
  `<genre>` is one word: `piano`, `handoff`, `incident`, `design`, `review`.
- Open documents stay here; closed ones move to `chiusi/` with `git mv`.
- A document is closed when its work is done, what remained open is an issue and a line
  in `STATUS.md`, and what is durable knowledge is in `docs/`.
- Every open document has an entry in `STATUS.md`.
- A journal document is never updated after it is written: what you learn goes to `docs/`.

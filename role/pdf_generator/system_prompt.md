# pdf_generator

Format approved artifacts into a PDF.

Run only after reviewer `PASS`. Do not add facts, conclusions, citations,
mathematical fixes, or unapproved content. If approval is absent, return an
error artifact to the OpenClaw planner.

Input should conform to `schemas/report_spec.schema.json`.

Until the real typesetter is installed, the Python module may emit a minimal
smoke-test PDF shell. It is a fallback artifact only.

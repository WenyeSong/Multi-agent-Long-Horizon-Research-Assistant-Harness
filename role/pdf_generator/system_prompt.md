# pdf_generator

Format approved artifacts into an HTML research report.

Write all report text, headings, captions, warnings, and errors in English
unless the planner explicitly requests another language.

Run only after reviewer `PASS`. Do not add facts, conclusions, citations,
mathematical fixes, or unapproved content. If approval is absent, return an
error artifact to the OpenClaw planner.

The role folder and compatibility entrypoint are still named `pdf_generator`
for existing planner routes. Treat that name as legacy: the current output is
HTML, produced by `html_generator.py`.

Input should conform to `schemas/report_spec.schema.json`.

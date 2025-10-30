# Slides & Docs

This folder contains slide-friendly and Confluence-ready documentation for the Identity Service.

- identity-service-slides.md — Marp-compatible Markdown slide deck
- confluence-identity-service.md — Copy/paste-friendly doc for Confluence

The architecture diagram used by the slides lives at:
- ../architecture/identity-service-flows.svg
- ../architecture/identity-service-flows.excalidraw.json

## Optional: Export slides to PDF/PNG (Marp)

If you want a PDF or PNG for Confluence or slides:

1) Install Marp CLI (Node.js required):

```zsh
npm install -g @marp-team/marp-cli
```

2) Export to PDF and PNG:

```zsh
marp identity-service-slides.md --pdf --output identity-service-slides.pdf
marp identity-service-slides.md --png --output identity-service-slides.png
```

Alternatively, use the Marp VS Code extension to export directly from the editor.

### GitHub Actions (auto export)

A workflow is included to export PDF and PNG on push to main:

- .github/workflows/export-identity-slides.yml

It uploads artifacts named `identity-service-slides` containing:

- docs/slides/identity-service-slides.pdf
- docs/slides/identity-service-slides.png

Trigger it by pushing slide changes or running it manually from the Actions tab.

## Tips for Confluence
- Drag-and-drop the SVG or exported PDF/PNG into the page
- Paste request/response blocks from the Confluence-ready doc
- Consider creating a parent page “Identity Service” and child pages for “Endpoints,” “Architecture,” and “Operations”

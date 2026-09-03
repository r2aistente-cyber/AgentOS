# Sample knowledge document

This folder shows the shape of a per-agent knowledge base. At runtime, an
agent's `knowledge/` directory is indexed into its RAG store (ChromaDB +
sentence-transformers) and its retrieval tools search it transparently.

Drop plain-text or Markdown files here, organized in any subfolder structure
you like — the indexer walks the tree. Keep documents focused; one topic per
file retrieves better than one large file.

## Example content

The Colombian Civil Code defines a contract as an act by which a party binds
itself toward another to give, to do, or not to do something. Each party may
be one or many persons. (Illustrative paraphrase — replace with your own
source material.)

---

The real project keeps its knowledge base out of version control
(`knowledge/` is gitignored). This `examples/` copy exists only to document
the expected layout.

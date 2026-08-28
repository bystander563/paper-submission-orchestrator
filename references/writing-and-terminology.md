# Writing Tone and Terminology

Use this reference during story lock, drafting, review, and final prose QA.

## Calibrated confidence, not defensive prose

Claim discipline controls what the paper says; it should not make every sentence
sound apologetic.

Prefer this paragraph rhythm:

1. state the scientific point directly;
2. give the evidence or mechanism;
3. state one interpretation-relevant boundary, if needed;
4. move broader caveats to Limitations.

Avoid:

- opening result paragraphs with disclaimers before naming the result;
- repeating the same exposure, scope, or non-SOTA caveat in every section;
- stacking `may`, `might`, `could`, `potentially`, and `suggests` when the
  evidence supports a clearer statement;
- using limitations as self-rejection rather than defining the valid scope;
- weakening established facts because a broader claim would be unsupported.

Use firm language for confirmed facts, conditional language for conditional
evidence, and explicit labels for exploratory or exposed results. One accurate
scope sentence is stronger than several vague hedges.

## Authoritative terminology

Source core terminology in this order:

1. official task or benchmark definitions;
2. primary papers that introduced or standardized the concept;
3. current authoritative venue or community standards;
4. plain descriptive language when no standard term exists.

Do not create a new scientific noun phrase merely to summarize several modules.
Do not rename an established task, metric, supervision setting, or shift type to
make the contribution sound larger. Keep internal code names and experiment
nicknames out of the manuscript unless they are the accepted method name.

A paper may name its new method. The method name must:

- reflect the actual mechanism or estimand;
- avoid collision with an established concept;
- be defined precisely on first use;
- not imply a broader capability than the experiments support;
- remain stable across abstract, method, tables, captions, and conclusion.

## Terminology audit questions

- Can each central term be traced to a primary source or benchmark definition?
- Is the term used with the same meaning as its source?
- Does a nearby field use the same term differently?
- Is an implementation detail being promoted into a scientific concept?
- Would plain language be clearer than a coined phrase?
- Are method name, task name, metric name, and claim scope kept distinct?

## Final prose audit

Flag passages where:

- the contribution is buried under caveats;
- the same limitation is repeated without adding information;
- unsupported novelty is carried by terminology rather than mechanism;
- a coined phrase lacks a definition or authoritative neighbor;
- a standard field term has been replaced by an idiosyncratic synonym;
- firm empirical facts are written as speculation, or exploratory evidence is
  written as fact.

export const metadata = {
  title: "About - DataPilot",
  description: "What DataPilot is, and what each stage of the pipeline actually does.",
};

const STAGE_DETAILS = [
  {
    name: "Guardrail",
    kicker: "Before anything else runs",
    body: "Every question is screened first - for length, for emptiness, and for prompt-injection or command attempts like \"ignore previous instructions.\" Anything that isn't recognisably a data question about this dataset is stopped here, before it can influence generation at all.",
  },
  {
    name: "Classify",
    kicker: "Is the question actually answerable, as written?",
    body: "The question is checked against what the dataset can support - customers and their orders. Clear questions pass straight through. Ambiguous ones, like \"best\" customer without a metric, pause here and come back to you as a clarifying question with suggested options.",
  },
  {
    name: "Generate",
    kicker: "Turning English into a query",
    body: "A retrieval step pulls the relevant schema and a handful of similar past queries, then the question is turned into a candidate SQL statement grounded in that context - not written freehand.",
  },
  {
    name: "Validate",
    kicker: "Checking the query, not just the question",
    body: "The generated SQL is checked before it ever touches the database: read-only, scoped to known tables and columns, and free of anything destructive. A query that fails this check is rejected here, never executed.",
  },
  {
    name: "Execute",
    kicker: "Running against real data",
    body: "Only a query that passed validation is run, against the mall purchase dataset, with a row limit so a broad question can't return an unbounded result.",
  },
  {
    name: "Format",
    kicker: "Turning rows back into an answer",
    body: "The raw result is turned into a plain-English summary, a table you can scan, and the exact SQL that produced it - so the answer is never just a claim, it's checkable.",
  },
];

export default function AboutPage() {
  return (
    <main className="about">
      <section className="page-intro">
        <p className="eyebrow">About the project</p>
        <h1 className="page-title">A pipeline, not a black box</h1>
        <p className="page-lede">
          DataPilot answers plain-English questions about a mall purchase dataset - customers and
          their orders - by turning them into SQL. The point isn&apos;t just getting an answer,
          it&apos;s being able to see exactly how the answer was produced, and to trust that
          nothing reached the database unchecked.
        </p>
      </section>

      <section className="about-why">
        <div className="about-why-card">
          <h2 className="doc-heading">Why a fixed pipeline</h2>
          <p className="doc-text">
            Letting a model write and run SQL directly is fast, but it collapses three different
            jobs - understanding the question, writing the query, and deciding it&apos;s safe to
            run - into one step with no seams to inspect. Splitting those jobs into stages means
            each one can be checked on its own, and a failure points at exactly where it happened.
          </p>
        </div>
        <div className="about-why-card">
          <h2 className="doc-heading">What the dataset covers</h2>
          <p className="doc-text">
            Two tables: <strong>customers</strong> (name, city, signup date) and{" "}
            <strong>orders</strong> (item purchased, category, amount spent, order date). Small on
            purpose - it&apos;s a testbed for the pipeline, not a production warehouse.
          </p>
        </div>
      </section>

      <section className="spine">
        {STAGE_DETAILS.map((stage, i) => (
          <div className="spine-row" key={stage.name}>
            <div className="spine-marker" aria-hidden="true">
              <span className="spine-index">{String(i + 1).padStart(2, "0")}</span>
              <span className="spine-dot" />
              {i < STAGE_DETAILS.length - 1 && <span className="spine-line" />}
            </div>
            <div className="spine-content">
              <p className="spine-kicker">{stage.kicker}</p>
              <h3 className="spine-name">{stage.name}</h3>
              <p className="spine-body">{stage.body}</p>
            </div>
          </div>
        ))}
      </section>
    </main>
  );
}
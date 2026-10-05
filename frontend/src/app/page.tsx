import Link from "next/link";

const SYSTEMS = [
  ["S1", "Executive Operations"],
  ["S2", "Marketing Intelligence"],
  ["S3", "Relationship Management"],
  ["S4", "Creator Economy"],
  ["S5", "Narrative Governance"],
  ["S6", "Audience Psychology"],
  ["S7", "Behavioral Consistency"],
  ["S8", "Persuasion Governance"],
  ["S9", "Voice & Presence"],
  ["S10", "Strategic Narrative"],
];

export default function HomePage() {
  return (
    <main className="relative min-h-screen overflow-hidden bg-[#04040D] text-[#D0D0EC]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_10%,rgba(107,63,251,.18),transparent_32%),radial-gradient(circle_at_85%_25%,rgba(0,212,255,.10),transparent_28%)]" />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-[#6B3FFB] to-transparent opacity-70" />

      <nav className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-6 py-6 lg:px-8">
        <div className="flex items-center gap-3">
          <span className="grid h-9 w-9 place-items-center rounded-xl border border-[#6B3FFB40] bg-[#6B3FFB12] text-lg text-[#9B78FF]">
            ⬡
          </span>
          <div>
            <div className="text-xs font-extrabold tracking-[0.32em] text-[#F0F0F8]">PAMASMMA</div>
            <div className="mt-1 font-mono text-[8px] tracking-[0.18em] text-[#4D4D78]">GOVERNED SYNTHETIC EXECUTIVE INTELLIGENCE</div>
          </div>
        </div>

        <Link
          href="/auth"
          className="rounded-xl border border-[#2A2A54] bg-[#0A0A1C] px-4 py-2.5 text-xs font-semibold text-[#DDE0F0] transition hover:border-[#6B3FFB80] hover:bg-[#10102A]"
        >
          Founder access →
        </Link>
      </nav>

      <section className="relative z-10 mx-auto grid max-w-6xl gap-14 px-6 pb-24 pt-10 lg:grid-cols-[1.15fr_.85fr] lg:items-center lg:px-8 lg:pt-20">
        <div>
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-[#3BFFA030] bg-[#3BFFA008] px-3 py-1.5 font-mono text-[9px] tracking-[0.18em] text-[#63DFAA]">
            <span className="h-1.5 w-1.5 rounded-full bg-[#3BFFA0] shadow-[0_0_8px_#3BFFA0]" />
            PRIVATE INTELLIGENCE SYSTEM · v4.1
          </div>

          <h1 className="max-w-4xl text-4xl font-semibold leading-[1.04] tracking-[-0.035em] text-[#F0F0F8] sm:text-5xl lg:text-7xl">
            Think in systems.
            <span className="block bg-gradient-to-r from-[#E8E8FA] via-[#9F8BFF] to-[#63D9FF] bg-clip-text text-transparent">
              Decide with memory.
            </span>
          </h1>

          <p className="mt-7 max-w-2xl text-base leading-8 text-[#74749B] sm:text-lg">
            PAMASMMA is a governed executive intelligence layer built to turn objectives,
            context, memory, reasoning, and action into one coherent operating loop.
          </p>

          <div className="mt-9 flex flex-wrap gap-3">
            <Link
              href="/auth"
              className="rounded-xl bg-[#6B3FFB] px-5 py-3 text-sm font-bold text-white shadow-[0_12px_40px_rgba(107,63,251,.25)] transition hover:bg-[#7951FF]"
            >
              Enter PAMASMMA
            </Link>
            <a
              href="#architecture"
              className="rounded-xl border border-[#29294D] bg-[#08081A] px-5 py-3 text-sm font-semibold text-[#A3A3C0] transition hover:border-[#454570] hover:text-[#E6E6F5]"
            >
              Explore the architecture
            </a>
          </div>

          <div className="mt-10 grid max-w-xl grid-cols-3 gap-3">
            {[
              ["10", "governed systems"],
              ["0-key", "kernel baseline"],
              ["AES-GCM", "secret protection"],
            ].map(([value, label]) => (
              <div key={value} className="rounded-2xl border border-[#191936] bg-[#08081A] p-4">
                <div className="font-mono text-sm font-bold text-[#E8E8FA]">{value}</div>
                <div className="mt-1 text-[10px] leading-4 text-[#51517A]">{label}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="relative">
          <div className="absolute -inset-10 rounded-full bg-[#6B3FFB12] blur-3xl" />
          <div className="relative overflow-hidden rounded-[28px] border border-[#242447] bg-[#07071A] shadow-[0_30px_100px_rgba(0,0,0,.45)]">
            <div className="flex items-center justify-between border-b border-[#181833] px-5 py-4">
              <div className="font-mono text-[9px] tracking-[0.2em] text-[#565680]">COGNITIVE CORE</div>
              <div className="flex items-center gap-2 font-mono text-[9px] text-[#54D6AB]">
                <span className="h-1.5 w-1.5 rounded-full bg-[#3BFFA0]" />
                READY
              </div>
            </div>
            <div className="grid grid-cols-[92px_1fr] gap-px bg-[#16162F]">
              <div className="bg-[#07071A] p-4 font-mono text-[9px] text-[#4B4B72]">
                <div>INPUT</div>
                <div className="mt-7">MEMORY</div>
                <div className="mt-7">REASONING</div>
                <div className="mt-7">ROUTER</div>
                <div className="mt-7">ACTION</div>
              </div>
              <div className="bg-[#07071A] p-5">
                <div className="rounded-2xl border border-[#6B3FFB35] bg-[#0A0A20] p-5">
                  <div className="font-mono text-[9px] tracking-[0.16em] text-[#6D6DA0]">EXECUTIVE FRAME</div>
                  <div className="mt-3 text-sm leading-7 text-[#D8D8E9]">
                    Objective → constraints → evidence → decision → action → feedback.
                  </div>
                </div>
                <div className="my-4 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-[#1B1B39] bg-[#0A0A20] p-4">
                    <div className="text-[10px] text-[#55557B]">Provider boundary</div>
                    <div className="mt-2 text-xs text-[#A9A9C7]">Kernel · local · optional cloud adapters</div>
                  </div>
                  <div className="rounded-2xl border border-[#1B1B39] bg-[#0A0A20] p-4">
                    <div className="text-[10px] text-[#55557B]">Durable path</div>
                    <div className="mt-2 text-xs text-[#A9A9C7]">PostgreSQL · pgvector · Valkey</div>
                  </div>
                </div>
                <div className="rounded-2xl border border-[#1B1B39] bg-[#0A0A20] p-4 font-mono text-[9px] leading-6 text-[#59597E]">
                  <span className="text-[#6B3FFB]">PAMASMMA</span> / governed / observable / testable
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="architecture" className="relative z-10 border-y border-[#111127] bg-[#050511]">
        <div className="mx-auto max-w-6xl px-6 py-20 lg:px-8">
          <div className="grid gap-10 lg:grid-cols-[.75fr_1.25fr]">
            <div>
              <div className="font-mono text-[9px] tracking-[0.24em] text-[#6B3FFB]">ARCHITECTURE</div>
              <h2 className="mt-4 text-3xl font-semibold tracking-tight text-[#ECECF8]">
                Intelligence is a layer, not a vendor.
              </h2>
              <p className="mt-4 max-w-lg text-sm leading-7 text-[#69698F]">
                Cognitive systems stay focused on their domain. Infrastructure, persistence,
                provider selection, validation, and event boundaries stay beneath them.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {[
                ["Context", "Identity, objectives, constraints and relevant memory."],
                ["Reasoning", "Plan, prioritize, compare and expose uncertainty."],
                ["Provider router", "Swap kernel, local or cloud intelligence without rewriting systems."],
                ["Governance", "Authentication, validation, action logs and controlled overrides."],
              ].map(([title, body]) => (
                <div key={title} className="rounded-2xl border border-[#191936] bg-[#08081A] p-5">
                  <div className="text-sm font-semibold text-[#DCDCED]">{title}</div>
                  <div className="mt-2 text-xs leading-6 text-[#5F5F84]">{body}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="relative z-10 mx-auto max-w-6xl px-6 py-20 lg:px-8">
        <div className="font-mono text-[9px] tracking-[0.24em] text-[#6B3FFB]">TEN COGNITIVE SYSTEMS</div>
        <div className="mt-7 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {SYSTEMS.map(([id, name]) => (
            <div key={id} className="group rounded-2xl border border-[#191936] bg-[#08081A] p-4 transition hover:-translate-y-0.5 hover:border-[#373760]">
              <div className="font-mono text-[9px] font-bold text-[#8B6CFF]">{id}</div>
              <div className="mt-2 text-xs leading-5 text-[#A6A6C2]">{name}</div>
            </div>
          ))}
        </div>
      </section>

      <footer className="relative z-10 border-t border-[#111127]">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-6 py-7 text-[10px] text-[#46466B] sm:flex-row sm:items-center sm:justify-between lg:px-8">
          <div>PAMASMMA · Governed Synthetic Executive Intelligence</div>
          <div className="font-mono">CIRVANNA · NAKURU, KENYA</div>
        </div>
      </footer>
    </main>
  );
}

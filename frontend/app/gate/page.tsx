export default async function Gate({ searchParams }: { searchParams: Promise<{ upgrade?: string }> }) {
  const sp = await searchParams;
  const upgrade = sp?.upgrade === "1";
  return (
    <div className="flex min-h-[70vh] w-full items-center justify-center text-center">
      <div className="max-w-md px-6">
        <img src="/logo.svg" alt="" className="mx-auto mb-5 h-14 w-14" />
        <h1 className="mb-2 text-[20px] font-semibold text-ink">ZoidLab MemoryMaker</h1>
        {upgrade ? (
          <p className="mb-6 text-[14px] leading-relaxed text-dim">
            Prompter is a <span className="text-ink">Nyquest Pro</span> workspace. Your account isn’t on a Pro or Teams
            plan yet — upgrade at <a className="text-cy" href="https://app.nyquest.ai/pricing">app.nyquest.ai/pricing</a> to get in.
          </p>
        ) : (
          <p className="mb-6 text-[14px] leading-relaxed text-dim">
            Sign in with your <span className="text-ink">Nyquest</span> account to design, govern, and deploy AI memory systems.
            Open ZoidLab from your Nyquest app (Pro or Teams).
          </p>
        )}
        <a href="https://app.nyquest.ai" className="inline-block rounded-lg bg-vi px-6 py-2.5 text-[13px] font-semibold text-white hover:opacity-90">
          Go to Nyquest →
        </a>
      </div>
    </div>
  );
}

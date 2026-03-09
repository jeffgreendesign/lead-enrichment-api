import LeadTester from "@/components/LeadTester";
import PipelineStats from "@/components/PipelineStats";
import RecentLeads from "@/components/RecentLeads";

export default function Home() {
  return (
    <div className="space-y-8">
      <section>
        <h2 className="mb-4 text-sm font-medium uppercase tracking-wider text-neutral-500">
          Lead Tester
        </h2>
        <LeadTester />
      </section>

      <div className="grid gap-8 md:grid-cols-2">
        <section>
          <h2 className="mb-4 text-sm font-medium uppercase tracking-wider text-neutral-500">
            Classification Split
          </h2>
          <RecentLeads />
        </section>

        <section>
          <h2 className="mb-4 text-sm font-medium uppercase tracking-wider text-neutral-500">
            Pipeline Stats
          </h2>
          <PipelineStats />
        </section>
      </div>
    </div>
  );
}

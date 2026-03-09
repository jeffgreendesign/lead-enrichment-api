import type { Metadata } from "next";
import LeadTester from "@/components/LeadTester";
import StatsSection from "@/components/StatsSection";
import { EnrichmentProvider } from "@/lib/EnrichmentContext";

export const metadata: Metadata = {
  title: "Dashboard",
  description: "Lead enrichment dashboard — test leads, view classification results and pipeline stats",
};

export default function Home() {
  return (
    <EnrichmentProvider>
      <div className="space-y-8">
        <section>
          <h2 className="mb-4 text-sm font-medium uppercase tracking-wider text-neutral-500">
            Lead Tester
          </h2>
          <LeadTester />
        </section>

        <StatsSection />
      </div>
    </EnrichmentProvider>
  );
}

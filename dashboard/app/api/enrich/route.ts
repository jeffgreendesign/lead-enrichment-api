import { NextResponse } from "next/server";

const LEAD_API_URL = process.env.LEAD_API_URL;

export async function POST(request: Request) {
  if (!LEAD_API_URL) {
    return NextResponse.json(
      { message: "LEAD_API_URL is not configured" },
      { status: 500 },
    );
  }

  const body = await request.json();

  const upstream = await fetch(`${LEAD_API_URL}/enrich`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await upstream.json();
  return NextResponse.json(data, { status: upstream.status });
}

import { NextResponse } from "next/server";

const LEAD_API_URL = process.env.LEAD_API_URL;

export async function POST(request: Request) {
  if (!LEAD_API_URL) {
    return NextResponse.json(
      { message: "LEAD_API_URL is not configured" },
      { status: 500 },
    );
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { message: "Invalid JSON in request body" },
      { status: 400 },
    );
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const requestId = request.headers.get("x-request-id");
  if (requestId) {
    headers["X-Request-ID"] = requestId;
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${LEAD_API_URL}/enrich`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });
  } catch (err) {
    return NextResponse.json(
      {
        message: `Failed to reach upstream API: ${err instanceof Error ? err.message : "unknown error"}`,
      },
      { status: 502 },
    );
  }

  let data: unknown;
  try {
    data = await upstream.json();
  } catch {
    return NextResponse.json(
      { message: `Upstream returned non-JSON response (${upstream.status})` },
      { status: 502 },
    );
  }

  return NextResponse.json(data, { status: upstream.status });
}

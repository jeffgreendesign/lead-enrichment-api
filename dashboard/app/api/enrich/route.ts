import { NextResponse } from "next/server";

const LEAD_API_URL = process.env.LEAD_API_URL?.replace(/\/+$/, "");

function withRequestId(
  response: NextResponse,
  requestId: string | null,
): NextResponse {
  if (requestId) {
    response.headers.set("X-Request-ID", requestId);
  }
  return response;
}

export async function POST(request: Request) {
  const requestId = request.headers.get("x-request-id");

  if (!LEAD_API_URL) {
    return withRequestId(
      NextResponse.json(
        { message: "LEAD_API_URL is not configured" },
        { status: 500 },
      ),
      requestId,
    );
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return withRequestId(
      NextResponse.json(
        { message: "Invalid JSON in request body" },
        { status: 400 },
      ),
      requestId,
    );
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (requestId) {
    headers["X-Request-ID"] = requestId;
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30_000);

  let upstream: Response;
  try {
    upstream = await fetch(`${LEAD_API_URL}/enrich`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      signal: controller.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      return withRequestId(
        NextResponse.json(
          { message: "Upstream API request timed out" },
          { status: 504 },
        ),
        requestId,
      );
    }
    return withRequestId(
      NextResponse.json(
        {
          message: `Failed to reach upstream API: ${err instanceof Error ? err.message : "unknown error"}`,
        },
        { status: 502 },
      ),
      requestId,
    );
  } finally {
    clearTimeout(timeout);
  }

  let data: unknown;
  try {
    data = await upstream.json();
  } catch {
    return withRequestId(
      NextResponse.json(
        { message: `Upstream returned non-JSON response (${upstream.status})` },
        { status: 502 },
      ),
      requestId,
    );
  }

  return withRequestId(
    NextResponse.json(data, { status: upstream.status }),
    requestId,
  );
}

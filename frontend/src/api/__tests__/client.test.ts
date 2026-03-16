import { describe, it, expect, vi, beforeEach } from "vitest";

const BASE = "http://localhost:8000";

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ projects: [] }),
      text: async () => "",
    })
  );
});

describe("listProjects", () => {
  it("calls correct endpoint", async () => {
    const { listProjects } = await import("../client");
    await listProjects();
    expect(fetch).toHaveBeenCalledWith(
      `${BASE}/api/v1/projects`,
      expect.objectContaining({ headers: expect.any(Object) })
    );
  });
});

describe("getGraph", () => {
  it("calls correct endpoint", async () => {
    const { getGraph } = await import("../client");
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ nodes: [], edges: [] }),
      text: async () => "",
    } as unknown as Response);
    await getGraph("proj-1");
    expect(fetch).toHaveBeenCalledWith(
      `${BASE}/api/v1/projects/proj-1/graph`,
      expect.any(Object)
    );
  });
});

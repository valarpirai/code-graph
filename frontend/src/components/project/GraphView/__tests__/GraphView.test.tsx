import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import GraphView from "../index";
import * as client from "../../../../api/client";

vi.mock("cytoscape-cose-bilkent", () => ({ default: {} }));
vi.mock("cytoscape", () => {
  const mockCy = vi.fn(() => ({
    on: vi.fn(),
    nodes: vi.fn(() => ({ forEach: vi.fn(), unselect: vi.fn() })),
    edges: vi.fn(() => ({ forEach: vi.fn() })),
    elements: vi.fn(() => ({ removeClass: vi.fn() })),
    destroy: vi.fn(),
    fit: vi.fn(),
    getElementById: vi.fn(() => ({ length: 0, select: vi.fn() })),
    animate: vi.fn(),
    extent: vi.fn(() => ({ x1: 0, y1: 0, x2: 100, y2: 100 })),
    off: vi.fn(),
  }));
  (mockCy as unknown as { use: ReturnType<typeof vi.fn> }).use = vi.fn();
  return { default: mockCy };
});

HTMLCanvasElement.prototype.getContext = vi.fn(() => null) as unknown as typeof HTMLCanvasElement.prototype.getContext;

const Wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={new QueryClient()}><MemoryRouter>{children}</MemoryRouter></QueryClientProvider>
);

describe("GraphView", () => {
  it("shows loading state initially", () => {
    vi.spyOn(client, "getGraph").mockReturnValue(new Promise(() => {}));
    vi.spyOn(client, "getClusters").mockReturnValue(new Promise(() => {}));
    render(<GraphView projectId="p1" />, { wrapper: Wrapper });
    expect(screen.getByText(/Loading graph/i)).toBeInTheDocument();
  });
});

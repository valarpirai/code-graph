import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";
import HierarchyView from "../index";
import * as client from "../../../../api/client";

const Wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>
);

describe("HierarchyView", () => {
  it("shows loading state", () => {
    vi.spyOn(client, "getGraph").mockReturnValue(new Promise(() => {}));
    render(<HierarchyView projectId="p1" />, { wrapper: Wrapper });
    expect(screen.getByText(/Building hierarchy/i)).toBeInTheDocument();
  });

  it("renders node labels", async () => {
    vi.spyOn(client, "getGraph").mockResolvedValue({
      nodes: [
        { data: { id: "n1", label: "main.py", node_type: "File" } },
        { data: { id: "n2", label: "MyClass", node_type: "Class" } },
      ],
      edges: [{ data: { id: "e1", source: "n1", target: "n2", relation: "containsFile" } }],
    });
    render(<HierarchyView projectId="p1" />, { wrapper: Wrapper });
    await screen.findByText("main.py");
  });
});

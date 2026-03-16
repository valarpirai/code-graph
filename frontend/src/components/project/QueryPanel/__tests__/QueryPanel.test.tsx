import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";
import QueryPanel from "../index";
import * as client from "../../../../api/client";

const Wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>
);

describe("QueryPanel", () => {
  it("renders run button", () => {
    render(<QueryPanel projectId="p1" />, { wrapper: Wrapper });
    expect(screen.getByRole("button", { name: /Run Query/i })).toBeInTheDocument();
  });

  it("shows results table after successful query", async () => {
    vi.spyOn(client, "runSparql").mockResolvedValue({
      variables: ["uri", "label"],
      results: {
        bindings: [
          { uri: { type: "uri", value: "http://ex/fn1" }, label: { type: "literal", value: "doThing" } },
        ],
      },
    });
    render(<QueryPanel projectId="p1" />, { wrapper: Wrapper });
    fireEvent.click(screen.getByRole("button", { name: /Run Query/i }));
    await waitFor(() => screen.getByText("doThing"));
    expect(screen.getByText("uri")).toBeInTheDocument();
  });
});

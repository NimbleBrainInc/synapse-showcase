import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import App from "../src/App";
import type { GuideState } from "../src/types";

const host = vi.hoisted(() => ({
  callTool: vi.fn(),
  openLink: vi.fn(),
  dataSync: undefined as undefined | (() => unknown),
}));
vi.mock("@nimblebrain/synapse/react", () => ({
  useApp: () => ({ callTool: host.callTool, openLink: host.openLink }),
  useDataSync: (callback: () => unknown) => {
    host.dataSync = callback;
  },
  useModelContext: () => undefined,
  useTheme: () => ({ mode: "light" }),
}));

const ids = ["welcome", "catalog", "control", "board", "appearance", "providers", "agents", "build"];
const guide = (overrides: Partial<GuideState> = {}): GuideState => ({
  revision: 1,
  step: "welcome",
  completed: [],
  skipped: [],
  pace: "guided",
  theme: "host",
  steps: ids.map((id) => ({ id, title: id, body: "", target: "" })),
  cards: [{ id: "c1", title: "First card", status: "todo" }],
  view: { zoom: 1, playing: false, focus: null },
  installation: {},
  apps: [],
  appJob: null,
  capabilities: {
    appPlan: true,
    appInstall: true,
    appStatus: true,
    appLifecycle: false,
    agentSetup: false,
  },
  catalog: [],
  ...overrides,
});
const ok = (data: unknown) => ({ isError: false, data });

let current: GuideState;
let calls: [string, Record<string, unknown>][];
beforeEach(() => {
  calls = [];
  vi.stubGlobal(
    "matchMedia",
    () => ({ matches: false, addEventListener: () => {}, removeEventListener: () => {} }),
  );
  host.callTool.mockImplementation(async (name: string, args: Record<string, unknown>) => {
    calls.push([name, args]);
    if (name === "guide_step" && !("complete" in args))
      current = { ...current, revision: current.revision + 1, step: String(args.step) };
    else if (name !== "guide_status") current = { ...current, revision: current.revision + 1 };
    return ok(current);
  });
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

test("quick pace: a chapter opened from the menu moves on to its quick neighbours", async () => {
  current = guide({ pace: "quick", step: "control" });
  render(<App />);
  const back = await screen.findByRole("button", { name: "Back" });
  expect((back as HTMLButtonElement).disabled).toBe(false);
  expect(screen.getByRole("button", { name: "Done, continue" })).toBeTruthy();

  fireEvent.click(screen.getByRole("button", { name: "Done, continue" }));
  await waitFor(() => expect(current.step).toBe("board"));
  expect(calls).toContainEqual(["guide_step", { step: "control", complete: true, skip: false }]);
  expect(calls.some(([name, args]) => name === "guide_step" && args.step === "welcome")).toBe(
    false,
  );
});

test("quick pace: Back from an opened chapter returns to the previous quick chapter", async () => {
  current = guide({ pace: "quick", step: "providers" });
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "Back" }));
  await waitFor(() => expect(current.step).toBe("board"));
});

test("a change notice refreshes the guide without clearing an unsent draft", async () => {
  current = guide({ step: "board" });
  render(<App />);
  const draft = await screen.findByLabelText("New practice task");
  fireEvent.change(draft, { target: { value: "Unsent idea" } });

  current = {
    ...current,
    revision: 2,
    cards: [...current.cards, { id: "c2", title: "Added by agent", status: "todo" }],
  };
  await act(async () => {
    await host.dataSync?.();
  });
  expect(await screen.findByText("Added by agent")).toBeTruthy();
  expect((screen.getByLabelText("New practice task") as HTMLInputElement).value).toBe("Unsent idea");
});

test("an app the host will not plan cannot be reviewed for installation", async () => {
  current = guide({
    step: "catalog",
    apps: [{ id: "crm", label: "CRM", installBlockedReason: "Your operator disabled installs." }],
  });
  render(<App />);
  expect(await screen.findByText("Your operator disabled installs.")).toBeTruthy();
  expect((screen.getByRole("button", { name: "Review installation" }) as HTMLButtonElement).disabled).toBe(true);
});

test("installing sends the reviewed plan hash with explicit confirmation", async () => {
  current = guide({ step: "catalog", apps: [{ id: "crm", label: "CRM" }] });
  const plan = {
    app: { id: "crm", label: "CRM", repo: "example/crm", commit: "abc123" },
    paths: { data: "/data/crm" },
    prerequisites: { docker: true },
    effects: ["Adds CRM"],
    planHash: "hash-1",
  };
  host.callTool.mockImplementation(async (name: string, args: Record<string, unknown>) => {
    calls.push([name, args]);
    return ok(name === "app_plan" ? plan : name === "app_install" ? {} : current);
  });
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "Review installation" }));
  fireEvent.click(await screen.findByRole("button", { name: "Install CRM" }));
  await waitFor(() =>
    expect(calls).toContainEqual(["app_install", { app: "crm", planHash: "hash-1", confirm: true }]),
  );
});

test("a missing prerequisite blocks installation", async () => {
  current = guide({ step: "catalog", apps: [{ id: "crm", label: "CRM" }] });
  const plan = {
    app: { id: "crm", label: "CRM", repo: "example/crm", commit: "abc123" },
    paths: { data: "/data/crm" },
    prerequisites: { docker: false },
    effects: [],
    planHash: "hash-1",
  };
  host.callTool.mockImplementation(async (name: string) =>
    ok(name === "app_plan" ? plan : current),
  );
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "Review installation" }));
  expect(await screen.findByText("Needed first: docker")).toBeTruthy();
  expect((screen.getByRole("button", { name: "Install CRM" }) as HTMLButtonElement).disabled).toBe(true);
});

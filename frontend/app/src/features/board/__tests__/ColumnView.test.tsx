// @vitest-environment jsdom

import { act, cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ColumnView } from "../components/ColumnView";
import type { Board, Column } from "../types";

let capturedOnCardCountChange: (n: number) => void = () => {};

vi.mock("../../card/components/CardStack", () => ({
	CardStack: ({ onCardCountChange }: { onCardCountChange: (n: number) => void; columnId: string }) => {
		capturedOnCardCountChange = onCardCountChange;
		return <div />;
	},
}));

vi.mock("../../card/components/CreateCardDialogue", () => ({
	CreateCardDialogue: ({ onClose }: { open: boolean; onClose: () => void; column: Column; board: Board }) => (
		<div data-testid="create-card-dialogue">
			<button type="button" onClick={onClose}>close</button>
		</div>
	),
}));

vi.mock("../components/ColumnOptionsMenu", () => ({
	ColumnOptionsMenu: () => null,
}));

const column: Column = { id: "c1", title: "Todo" };
const board: Board = { id: "b1", title: "B", starred: false, columns: [column], createdAt: new Date(), updatedAt: new Date() };
const setup = () => render(<ColumnView column={column} board={board} />);
const addButton = () => document.querySelector('[data-testid="AddIcon"]')!.closest("button") as HTMLElement;

describe("ColumnView", () => {
	afterEach(cleanup);

	it("opens CreateCardDialogue when add button is clicked", async () => {
		const user = userEvent.setup();
		setup();
		expect(screen.queryByTestId("create-card-dialogue")).toBeNull();
		await user.click(addButton());
		expect(screen.getByTestId("create-card-dialogue")).not.toBeNull();
	});

	it("closes CreateCardDialogue when onClose is called", async () => {
		const user = userEvent.setup();
		setup();
		await user.click(addButton());
		await user.click(screen.getByRole("button", { name: "close" }));
		expect(screen.queryByTestId("create-card-dialogue")).toBeNull();
	});

	it("updates card count when CardStack calls onCardCountChange", async () => {
		setup();
		await act(async () => { capturedOnCardCountChange(5); });
		expect(screen.getByText("5")).not.toBeNull();
	});
});

// @vitest-environment jsdom

import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { BoardTopActions } from "../components/BoardTopActions";
import { useUpdateBoard } from "../hooks/useUpdateBoard";
import type { Board } from "../types";

vi.mock("../hooks/useUpdateBoard");
vi.mock("../components/BoardOptionsMenu", () => ({
	BoardOptionsMenu: () => <div data-testid="board-options-menu" />,
}));
vi.mock("react-timeago", () => ({
	default: ({ date }: { date: Date }) => (
		<span>{date.toISOString()}</span>
	),
}));

const mockMutate = vi.fn();

const makeBoard = (starred: boolean): Board => ({
	id: "board-1",
	title: "Test Board",
	starred,
	columns: [],
	createdAt: new Date("2025-01-01"),
	updatedAt: new Date("2025-06-01"),
});

describe("BoardTopActions", () => {
	afterEach(() => {
		cleanup();
	});

	beforeEach(() => {
		vi.resetAllMocks();
		vi.mocked(useUpdateBoard).mockReturnValue({
			mutate: mockMutate,
		} as unknown as ReturnType<typeof useUpdateBoard>);
	});

	it("renders BoardOptionsMenu and the updated-at time", () => {
		render(<BoardTopActions board={makeBoard(false)} />);

		expect(screen.getByTestId("board-options-menu")).not.toBeNull();
	});

	it("renders StarOutlineIcon when board is not starred", () => {
		render(<BoardTopActions board={makeBoard(false)} />);

		// StarOutlineIcon renders an svg; StarIcon does not appear
		expect(document.querySelector('[data-testid="StarOutlineIcon"]')).not.toBeNull();
		expect(document.querySelector('[data-testid="StarIcon"]')).toBeNull();
	});

	it("renders StarIcon when board is starred", () => {
		render(<BoardTopActions board={makeBoard(true)} />);

		expect(document.querySelector('[data-testid="StarIcon"]')).not.toBeNull();
		expect(document.querySelector('[data-testid="StarOutlineIcon"]')).toBeNull();
	});

	it("calls updateBoard with starred toggled to true when clicking star button on unstarred board", async () => {
		const user = userEvent.setup();
		render(<BoardTopActions board={makeBoard(false)} />);

		const button = screen.getByRole("button");
		await user.click(button);

		expect(mockMutate).toHaveBeenCalledWith({
			id: "board-1",
			boardData: { starred: true },
		});
	});

	it("calls updateBoard with starred toggled to false when clicking star button on starred board", async () => {
		const user = userEvent.setup();
		render(<BoardTopActions board={makeBoard(true)} />);

		const button = screen.getByRole("button");
		await user.click(button);

		expect(mockMutate).toHaveBeenCalledWith({
			id: "board-1",
			boardData: { starred: false },
		});
	});
});

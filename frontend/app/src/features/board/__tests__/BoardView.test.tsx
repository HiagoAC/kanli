// @vitest-environment jsdom

import type { DragEndEvent } from "@dnd-kit/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, render, screen } from "@testing-library/react";
import type React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
	executeDragMove,
	updateItemsOrder,
} from "../../../utils/drag-and-drop";
import { BoardView } from "../components/BoardView";
import type { Board, Column } from "../types";

// Capture the latest onDragEnd so tests can fire it manually
let capturedOnDragEnd: ((event: DragEndEvent) => void) | undefined;

vi.mock("@dnd-kit/core", async () => {
	const actual =
		await vi.importActual<typeof import("@dnd-kit/core")>("@dnd-kit/core");

	return {
		...actual,
		// biome-ignore lint/suspicious/noExplicitAny: Mocking requires any for simplified test component props
		DndContext: ({ onDragEnd, children }: any) => {
			capturedOnDragEnd = onDragEnd;
			return <div>{children}</div>;
		},
	};
});

const mockMoveColumnBefore = vi.fn();
const mockMoveColumnEnd = vi.fn();

vi.mock("../hooks/useMoveColumnBefore", () => ({
	useMoveColumnBefore: () => ({ mutate: mockMoveColumnBefore }),
}));

vi.mock("../hooks/useMoveColumnEnd", () => ({
	useMoveColumnEnd: () => ({ mutate: mockMoveColumnEnd }),
}));

vi.mock("../../../utils/drag-and-drop", () => ({
	executeDragMove: vi.fn(),
	updateItemsOrder: vi.fn(),
}));

vi.mock("../components/BoardTopBar", () => ({
	BoardTopBar: ({ board }: { board: Board }) => (
		<div data-testid="board-title">{board.title}</div>
	),
}));

vi.mock("../components/SortableColumn", () => ({
	SortableColumn: ({
		children,
	}: {
		children: (props: {
			dragListeners: Record<string, unknown>;
		}) => React.ReactNode;
	}) => <div>{children({ dragListeners: {} })}</div>,
}));

vi.mock("../components/ColumnView", () => ({
	ColumnView: ({ column }: { column: Column }) => (
		<div data-testid={`column-${column.id}`}>{column.title}</div>
	),
}));

const column = (id: string, title: string): Column => ({ id, title });

const board = (columns: Column[]): Board => ({
	id: "board-1",
	title: "Test Board",
	starred: false,
	columns,
	createdAt: new Date(),
	updatedAt: new Date(),
});

const renderBoard = (b: Board) =>
	render(
		<QueryClientProvider client={new QueryClient()}>
			<BoardView board={b} />
		</QueryClientProvider>,
	);

describe("BoardView", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	afterEach(() => {
		cleanup();
	});

	it("renders board title", () => {
		renderBoard(board([column("col-1", "To Do")]));

		expect(screen.getByTestId("board-title")).toBeTruthy();
		expect(screen.getByText("Test Board")).toBeTruthy();
	});

	it("renders all columns", () => {
		renderBoard(
			board([
				column("col-1", "To Do"),
				column("col-2", "In Progress"),
				column("col-3", "Done"),
			]),
		);

		expect(screen.getByTestId("column-col-1")).toBeTruthy();
		expect(screen.getByTestId("column-col-2")).toBeTruthy();
		expect(screen.getByTestId("column-col-3")).toBeTruthy();
	});

	it("renders empty board", () => {
		renderBoard(board([]));

		expect(screen.getByTestId("board-title")).toBeTruthy();
		expect(screen.queryByTestId(/column-/)).toBeNull();
	});

	it("does not update columns when executeDragMove returns false", async () => {
		vi.mocked(executeDragMove).mockReturnValue(false);

		renderBoard(board([column("col-1", "To Do"), column("col-2", "Done")]));

		await act(async () => {
			capturedOnDragEnd?.({ active: { id: "col-1" }, over: { id: "col-2" } } as DragEndEvent);
		});

		expect(executeDragMove).toHaveBeenCalled();
		expect(updateItemsOrder).not.toHaveBeenCalled();
	});

	it("updates columns order when executeDragMove returns true", async () => {
		vi.mocked(executeDragMove).mockReturnValue(true);
		vi.mocked(updateItemsOrder).mockImplementation((items) => items);

		renderBoard(board([column("col-1", "To Do"), column("col-2", "Done")]));

		await act(async () => {
			capturedOnDragEnd?.({ active: { id: "col-1" }, over: { id: "col-2" } } as DragEndEvent);
		});

		expect(executeDragMove).toHaveBeenCalled();
		expect(updateItemsOrder).toHaveBeenCalled();
	});

	describe("handleDragEnd callbacks with executeDragMove", () => {
		beforeEach(async () => {
			const actual = await vi.importActual<typeof import("../../../utils/drag-and-drop")>(
				"../../../utils/drag-and-drop",
			);
			vi.mocked(executeDragMove).mockImplementation(actual.executeDragMove);
			vi.mocked(updateItemsOrder).mockImplementation(actual.updateItemsOrder);
		});

		it("calls moveColumnBefore when dragging a column upward (moveItemAbove)", async () => {
			// col-3 (index 2) dragged over col-1 (index 0) → isMovingUp=true → moveItemAbove
			renderBoard(
				board([
					column("col-1", "To Do"),
					column("col-2", "In Progress"),
					column("col-3", "Done"),
				]),
			);

			await act(async () => {
				capturedOnDragEnd?.({ active: { id: "col-3" }, over: { id: "col-1" } } as DragEndEvent);
			});

			expect(mockMoveColumnBefore).toHaveBeenCalledWith({
				columnId: "col-3",
				boardId: "board-1",
				targetColumnId: "col-1",
			});
			expect(mockMoveColumnEnd).not.toHaveBeenCalled();
		});

		it("calls moveColumnEnd when dragging a column to the last position (moveItemBottom)", async () => {
			// col-1 (index 0) dragged over col-2 (index 1, last) → overIndex===length-1 → moveItemBottom
			renderBoard(
				board([
					column("col-1", "To Do"),
					column("col-2", "Done"),
				]),
			);

			await act(async () => {
				capturedOnDragEnd?.({ active: { id: "col-1" }, over: { id: "col-2" } } as DragEndEvent);
			});

			expect(mockMoveColumnEnd).toHaveBeenCalledWith({
				columnId: "col-1",
				boardId: "board-1",
			});
			expect(mockMoveColumnBefore).not.toHaveBeenCalled();
		});
	});
});

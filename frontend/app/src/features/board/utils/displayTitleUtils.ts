import type { BoardListItem } from "../types";

/**
 * Maps each board ID to a unique display title.
 * Boards sharing a title are disambiguated by appending a numeric suffix,
 * sorted by creation date (e.g. "My Board", "My Board (1)").
 */
export function generateDisplayTitles(
	boards: BoardListItem[],
): Map<string, string> {
	const titleGroups = new Map<string, BoardListItem[]>();
	const displayTitles = new Map<string, string>();

	for (const board of boards) {
		if (!titleGroups.has(board.title)) {
			titleGroups.set(board.title, []);
		}
		titleGroups.get(board.title)?.push(board);
	}

	for (const [title, boardsWithSameTitle] of titleGroups) {
		if (boardsWithSameTitle.length === 1) {
			displayTitles.set(boardsWithSameTitle[0].id, title);
		} else {
			const sortedBoards = boardsWithSameTitle.sort(
				(a, b) =>
					new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime(),
			);
			sortedBoards.forEach((board, index) => {
				if (index === 0) {
					displayTitles.set(board.id, title);
				} else {
					displayTitles.set(board.id, `${title} (${index})`);
				}
			});
		}
	}

	return displayTitles;
}

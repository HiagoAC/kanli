// @vitest-environment jsdom

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { UserInfo } from "../components/UserInfo";

describe("UserInfo", () => {
	it("calls refreshUser when avatar fails to load", () => {
		const refreshUser = vi.fn();
		const user = {
			id: "1",
			username: "johndoe",
			firstName: "John",
			lastName: "Doe",
			email: "john@example.com",
			avatarUrl: "https://example.com/avatar.jpg",
			isGuest: false,
		};

		render(<UserInfo user={user} refreshUser={refreshUser} />);

		const avatar = screen.getByAltText("John Doe");

		fireEvent.error(avatar);

		expect(refreshUser).toHaveBeenCalledTimes(1);
	});

	it("renders initials when avatarUrl is undefined", () => {
		const user = {
			id: "1",
			username: "johndoe",
			firstName: "John",
			lastName: "Doe",
			email: "john@example.com",
			avatarUrl: undefined,
			isGuest: false,
		};

		render(<UserInfo user={user} />);

		expect(screen.getByText("JD")).not.toBeNull();
	});
});

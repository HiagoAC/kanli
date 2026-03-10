// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Mock } from "vitest";
import apiClient, { BASE_URL } from "../../../services/apiClient";
import * as authServices from "../services";

vi.mock("../../../services/apiClient", () => ({
	default: {
		post: vi.fn(),
		get: vi.fn(),
	},
	BASE_URL: "http://localhost:8000/",
}));

describe("signInWithGoogle", () => {
	let assignMock: Mock;
	let originalLocation: Location;
	let mockApiPost: Mock;
	let mockApiGet: Mock;

	beforeEach(() => {
		assignMock = vi.fn();
		originalLocation = window.location;
		Object.defineProperty(window, "location", {
			value: {
				...originalLocation,
				assign: assignMock,
			},
			writable: true,
		});

		mockApiPost = vi.mocked(apiClient.post);
		mockApiGet = vi.mocked(apiClient.get);

		mockApiPost.mockResolvedValue({ data: {} });
		mockApiGet.mockResolvedValue({ data: { isGuest: false } });
	});

	afterEach(() => {
		Object.defineProperty(window, "location", {
			value: originalLocation,
			writable: true,
		});
		vi.clearAllMocks();
	});

	it("should call window.location.assign with Google OAuth URL", () => {
		authServices.signInWithGoogle();

		expect(assignMock).toHaveBeenCalledOnce();
		expect(assignMock).toHaveBeenCalledWith(
			`${BASE_URL}social-auth/login/google-oauth2/`,
		);
	});

	it("should not throw any errors when called without parameters", () => {
		expect(() => authServices.signInWithGoogle()).not.toThrow();
	});

	it("should not set guest action when no guestAction parameter provided", async () => {
		await authServices.signInWithGoogle();

		expect(mockApiGet).not.toHaveBeenCalled();
		expect(mockApiPost).not.toHaveBeenCalled();
		expect(assignMock).toHaveBeenCalledOnce();
	});

	it("should not set guest action when guestAction provided but user is not a guest", async () => {
		mockApiGet.mockResolvedValue({ data: { isGuest: false } });

		await authServices.signInWithGoogle("merge");

		expect(mockApiGet).toHaveBeenCalledWith("me/");
		expect(mockApiPost).not.toHaveBeenCalled();
		expect(assignMock).toHaveBeenCalledOnce();
	});

	it("should set guest action when guestAction provided and user is a guest", async () => {
		mockApiGet.mockResolvedValue({ data: { isGuest: true } });

		await authServices.signInWithGoogle("merge");

		expect(mockApiGet).toHaveBeenCalledWith("me/");
		expect(mockApiPost).toHaveBeenCalledWith("session/guest-action/", {
			guest_action: "merge",
		});
		expect(assignMock).toHaveBeenCalledOnce();
	});

	it("should set guest action with 'discard' when specified", async () => {
		mockApiGet.mockResolvedValue({ data: { isGuest: true } });

		await authServices.signInWithGoogle("discard");

		expect(mockApiGet).toHaveBeenCalledWith("me/");
		expect(mockApiPost).toHaveBeenCalledWith("session/guest-action/", {
			guest_action: "discard",
		});
		expect(assignMock).toHaveBeenCalledOnce();
	});

	it("should continue with sign-in even if setGuestAction fails", async () => {
		mockApiGet.mockResolvedValue({ data: { isGuest: true } });
		mockApiPost.mockRejectedValue(new Error("Network error"));
		const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

		await authServices.signInWithGoogle("merge");

		expect(mockApiPost).toHaveBeenCalledWith("session/guest-action/", {
			guest_action: "merge",
		});
		expect(consoleSpy).toHaveBeenCalledWith(
			"Failed to set guest action:",
			expect.any(Error),
		);
		expect(assignMock).toHaveBeenCalledOnce();

		consoleSpy.mockRestore();
	});
});

describe("logout", () => {
	let mockApiPost: Mock;

	beforeEach(() => {
		mockApiPost = vi.mocked(apiClient.post);
		mockApiPost.mockResolvedValue({});
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	it("should call apiClient.post with logout URL", async () => {
		await authServices.logout();

		expect(mockApiPost).toHaveBeenCalledOnce();
		expect(mockApiPost).toHaveBeenCalledWith("logout/");
	});
});

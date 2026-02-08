import { render, screen } from "@testing-library/react";

import App from "./App";

describe("App", () => {
  it("renders studio heading and auth section", () => {
    render(<App />);
    expect(screen.getByText("story_gen studio")).toBeInTheDocument();
    expect(screen.getByText("Auth")).toBeInTheDocument();
    expect(screen.getByText("Story Blueprints")).toBeInTheDocument();
  });
});

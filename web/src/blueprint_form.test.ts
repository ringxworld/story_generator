import { applyBlueprintToForm, buildBlueprintFromForm, emptyStoryForm } from "./blueprint_form";

describe("blueprint form conversion", () => {
  it("builds a blueprint from form text blocks", () => {
    const form = {
      ...emptyStoryForm(),
      title: "The Missing Ledger",
      premise: "A city questions its own records.",
      canonRulesRaw: "No supernatural causes.\nCouncil has seven members.",
      themesRaw: "memory|Memory can be altered.|1",
      charactersRaw: "rhea|investigator|Find the ledger",
      chaptersRaw: "ch01|The Missing Ledger|Introduce contradiction|memory|rhea|",
    };

    const blueprint = buildBlueprintFromForm(form);
    expect(blueprint.premise).toBe("A city questions its own records.");
    expect(blueprint.themes[0].key).toBe("memory");
    expect(blueprint.characters[0].key).toBe("rhea");
    expect(blueprint.chapters[0].key).toBe("ch01");
  });

  it("round-trips blueprint data back into form strings", () => {
    const original = buildBlueprintFromForm({
      ...emptyStoryForm(),
      title: "x",
      premise: "Premise",
      canonRulesRaw: "Rule A",
      themesRaw: "memory|Memory can be altered.|1",
      charactersRaw: "rhea|investigator|Find the ledger",
      chaptersRaw: "ch01|Title|Objective|memory|rhea|",
    });
    const form = applyBlueprintToForm("Story", original);
    const rebuilt = buildBlueprintFromForm(form);
    expect(rebuilt).toEqual(original);
  });

  it("fails on malformed rows", () => {
    expect(() =>
      buildBlueprintFromForm({
        ...emptyStoryForm(),
        title: "x",
        premise: "Premise",
        canonRulesRaw: "",
        themesRaw: "broken-theme-row",
        charactersRaw: "",
        chaptersRaw: "",
      }),
    ).toThrow("Theme rows must use");
  });
});
